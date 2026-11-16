# Databricks notebook source
##################################################################################
# Create Quality Monitor Notebook
##
# Parameters:

# Required fields
# * table_name  - A 3 level Unity Catalog tablename you want to monitor {catalog}.{schema}.{table}
# * assets_dir - The directory to store monitoring assets (e.g. dashboard, metric tables).
# * output_schema_name - Schema where output metric tables are created.

# Optional fields
# * baseline_table_name - Name of the baseline table from which drift metrics are computed from. Columns in the monitored table should also be present in the baseline table.
# * custom_metrics - Custom metrics to compute on the monitored table. These can be aggregate metrics, derived metrics (from already computed aggregate metrics), or drift metrics (comparing metrics across time windows). https://databricks-sdk-py.readthedocs.io/en/stable/dbdataclasses/catalog.html#databricks.sdk.service.catalog.MonitorMetric
# * data_classification_config - The data classification config for the monitor. https://databricks-sdk-py.readthedocs.io/en/stable/dbdataclasses/catalog.html#databricks.sdk.service.catalog.MonitorDataClassificationConfig
# * inference_log - Configuration for monitoring inference logs. https://databricks-sdk-py.readthedocs.io/en/stable/dbdataclasses/catalog.html#databricks.sdk.service.catalog.MonitorInferenceLog
# * notifications - The notification settings for the monitor. https://databricks-sdk-py.readthedocs.io/en/stable/dbdataclasses/catalog.html#databricks.sdk.service.catalog.MonitorNotifications
# * schedule - The schedule for automatically updating and refreshing metric tables. https://databricks-sdk-py.readthedocs.io/en/stable/dbdataclasses/catalog.html#databricks.sdk.service.catalog.MonitorCronSchedule
# * skip_builtin_dashboard - Whether to skip creating a default dashboard summarizing data quality metrics.
# * slicing_exprs - List of column expressions to slice data with for targeted analysis. The data is grouped by each expression independently, resulting in a separate slice for each predicate and its complements. For high-cardinality columns, only the top 100 unique values by frequency will generate slices.
# * snapshot - Configuration for monitoring snapshot tables. https://databricks-sdk-py.readthedocs.io/en/stable/dbdataclasses/catalog.html#databricks.sdk.service.catalog.MonitorSnapshot
# * time_series - Configuration for monitoring time series tables. https://databricks-sdk-py.readthedocs.io/en/stable/dbdataclasses/catalog.html#databricks.sdk.service.catalog.MonitorTimeSeries
# * warehouse_id - Optional argument to specify the warehouse for dashboard creation. If not specified, the first running warehouse will be used.
#
##################################################################################

# COMMAND ----------

dbutils.widgets.dropdown("CATALOG", "dev_datascience", ["dev_datascience", "staging_datascience", "prod_datascience"], "Catalog Name")

dbutils.widgets.text(
    "SCHEMA", "monitoring", label="Schema Name"
) 

# monitoring table name (without "_inference" suffix)
#CHANGEME: Change this to your short model name 
dbutils.widgets.text(
    "SHORT_MODEL_NAME", "", label="Model Name"
) 

dbutils.widgets.text(
    "ASSETS_DIR", "/MLOps/databricks_lakehouse_monitoring", label="Asset Directory"
)

# COMMAND ----------

# MAGIC  %pip install -U "databricks-sdk>=0.28.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# Get config parameters
import os
import sys

notebook_path = '/Workspace/' + os.path.dirname(dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get())

# Change the working directory to notebook_path
os.chdir(notebook_path)
print(notebook_path)

# Move one directory up
os.chdir('..')
print(os.getcwd())

# Append the new path to sys.path
sys.path.append("../..")

# COMMAND ----------

# Import configuration parameters
from config import (
    GRANULARITIES, MODEL_ID_COL, PREDICTION_COL, LABEL_COL, PROBLEM_TYPE, TIMESTAMP_COL, EMAIL_ADDRESSES, QUARTZ_CRON_EXPRESSION, TIMEZONE_ID
)

CATALOG = dbutils.widgets.get("CATALOG")
SCHEMA = dbutils.widgets.get("SCHEMA")
SHORT_MODEL_NAME =dbutils.widgets.get("SHORT_MODEL_NAME")
TABLE_NAME = f"{CATALOG}.{SCHEMA}.{SHORT_MODEL_NAME}_inference"
ASSETS_DIR = dbutils.widgets.get("ASSETS_DIR")
OUTPUT_SCHEMA_NAME = f"{CATALOG}.{SCHEMA}"


# COMMAND ----------

# Find dashboard_id
import requests

# Fill these in with your workspace info and token
DATABRICKS_HOST = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiUrl().getOrElse(None)
# Retrieve the current user's temporary API token
DATABRICKS_TOKEN = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().getOrElse(None)

headers = {
    "Authorization": f"Bearer {DATABRICKS_TOKEN}"
}
def fetch_all_dashboards(DATABRICKS_HOST, headers):
    dashboards = []
    next_page_token = None

    while True:
        url = f"{DATABRICKS_HOST}/api/2.0/lakeview/dashboards"
        params = {'page_size': 1000}
        if next_page_token:
            params['page_token'] = next_page_token
            print(f"Rate limited! Waiting 1 seconds before next page request...")
            time.sleep(1) #rate limited
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        dashboards.extend(data.get('dashboards', []))
        next_page_token = data.get('next_page_token')
        if not next_page_token:
            break

    return dashboards

def find_dashboard_id_by_name(DATABRICKS_HOST, headers, target_name):
    dashboards = fetch_all_dashboards(DATABRICKS_HOST, headers)
    for dashboard in dashboards:
        # Some APIs use 'name', some use 'title'. Adjust as needed.
        if dashboard.get('display_name') == target_name:
            return dashboard.get('dashboard_id')
    return None

# This is the name of the dashboard in the yml resource file
# mn
#CHANGEME: Change this to your dashboard name 
dashboard_name = ""
DASHBOARD_ID = find_dashboard_id_by_name(DATABRICKS_HOST, headers, dashboard_name)
print("Dashboard ID:", DASHBOARD_ID)


# COMMAND ----------

from databricks.sdk.service.catalog import MonitorMetric, MonitorMetricType
from pyspark.sql import types as T

#CHANGEME: Change this to your custom metrics
CUSTOM_METRICS = [
    MonitorMetric(
        type=MonitorMetricType.CUSTOM_METRIC_TYPE_AGGREGATE,
        name="accuracy",
        input_columns=[":table"],
        definition=f"""AVG(
            CASE WHEN {PREDICTION_COL} = {LABEL_COL} THEN 1 ELSE 0 END
            )""",
        output_data_type=T.StructField("accuracy", T.DoubleType()).json(),
    ),
]



# COMMAND ----------

import time
from pprint import pprint
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import MonitorInferenceLog, MonitorInferenceLogProblemType, MonitorNotifications, MonitorDestination, MonitorCronSchedule, MonitorInfoStatus, MonitorRefreshInfoState
from databricks.sdk.errors import ResourceDoesNotExist

w = WorkspaceClient()

def check_monitor_exists(workspace_client, table_name):
    try:
        workspace_client.quality_monitors.get(table_name=table_name)
        return True
    except ResourceDoesNotExist:
        return False

def create_or_update_monitor(workspace_client, table_name, output_schema_name, custom_metrics, inference_log, notifications, schedule,dashboard_id):    
    monitor_exists = check_monitor_exists(workspace_client, table_name)
    print(f"Monitor exists: {monitor_exists}")

    if monitor_exists:
        # If it exists, update it with the updated variables
        workspace_client.quality_monitors.update(
            table_name=table_name,
            output_schema_name=output_schema_name,
            inference_log=inference_log,
            notifications=notifications,
            schedule=schedule,
            custom_metrics=custom_metrics,
            dashboard_id = dashboard_id
        )
        print("Quality Monitor Info after update:")
    else:
        # If the monitor does not exist, create a new one
        workspace_client.quality_monitors.create(
            table_name=table_name,
            assets_dir=ASSETS_DIR,
            output_schema_name=output_schema_name,
            inference_log=inference_log,
            notifications=notifications,
            schedule=schedule,
            custom_metrics=custom_metrics
        )
        print("Quality Monitor Info after creation:")

    # Initialize info variable
    info = workspace_client.quality_monitors.get(table_name=table_name)

    # Wait for monitor to be created
    while info.status == MonitorInfoStatus.MONITOR_STATUS_PENDING:
        info = workspace_client.quality_monitors.get(table_name=table_name)
        time.sleep(10)

    assert info.status == MonitorInfoStatus.MONITOR_STATUS_ACTIVE, "Error creating monitor"

    # It does not allow us to add the dashboard_id on a new monitor so we replace it here
    if dashboard_id != info.dashboard_id:
        print("Monitor dashboard_id does not match expected value")
        workspace_client.quality_monitors.update(
            table_name=table_name,
            output_schema_name=output_schema_name,
            inference_log=inference_log,
            dashboard_id = dashboard_id
        )
        # Validate success again
        info = workspace_client.quality_monitors.get(table_name=table_name)
        while info.status == MonitorInfoStatus.MONITOR_STATUS_PENDING:
            info = workspace_client.quality_monitors.get(table_name=table_name)
            time.sleep(10)
        assert info.status == MonitorInfoStatus.MONITOR_STATUS_ACTIVE, "Error creating monitor"
        print("Monitor dashboard_id updated:")
    else:
        print("Monitor dashboard_id matches expected value")

    pprint(info)

    # A metric refresh will automatically be triggered on creation
    refreshes = workspace_client.quality_monitors.list_refreshes(table_name=table_name).refreshes
    assert(len(refreshes) > 0)

    run_info = refreshes[0]
    while run_info.state in (MonitorRefreshInfoState.PENDING, MonitorRefreshInfoState.RUNNING):
        run_info = workspace_client.quality_monitors.get_refresh(table_name=table_name, refresh_id=run_info.refresh_id)
        time.sleep(30)

    assert run_info.state == MonitorRefreshInfoState.SUCCESS, "Monitor refresh failed"

# Define the parameters
inference_log = MonitorInferenceLog(
    timestamp_col=TIMESTAMP_COL,
    granularities=GRANULARITIES,
    model_id_col=MODEL_ID_COL,
    problem_type=MonitorInferenceLogProblemType(PROBLEM_TYPE),
    prediction_col=PREDICTION_COL,
    label_col=LABEL_COL
)

notifications = MonitorNotifications(
    on_failure=MonitorDestination(
        email_addresses=EMAIL_ADDRESSES
    )
)

schedule = MonitorCronSchedule(
    quartz_cron_expression=QUARTZ_CRON_EXPRESSION,
    timezone_id=TIMEZONE_ID
)

# Call the function
create_or_update_monitor(w, TABLE_NAME, OUTPUT_SCHEMA_NAME, CUSTOM_METRICS, inference_log, notifications, schedule,DASHBOARD_ID)

# COMMAND ----------

spark.sql(f"""ALTER TABLE {TABLE_NAME} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)""")
