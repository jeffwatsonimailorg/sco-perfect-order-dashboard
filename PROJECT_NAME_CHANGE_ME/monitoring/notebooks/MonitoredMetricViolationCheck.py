# Databricks notebook source
#CHANGEME: Replace with your own thresholds 
metric_threshold = {
    "METRIC": 0,
}

metrics = ", ".join(metric_threshold.keys())
thresholds = ", ".join(map(str, metric_threshold.values()))

# COMMAND ----------

##################################################################################
# This notebook runs a sql query and set the result as job task value
#
# This notebook has the following parameters:
#
#  * table_name_under_monitor (required)  - The name of a table that is currently being monitored
#  * metric_to_monitor (required)  - Metric to be monitored for threshold violation
#  * metric_violation_threshold (required)  - Threshold value for metric violation
#  * num_evaluation_windows (required)  - Number of windows to check for violation
#  * num_violation_windows (required)  - Number of windows that need to violate the threshold
##################################################################################

# List of input args needed to run the notebook as a job.
# Provide them via DB widgets or notebook arguments.
#
# Name of the table that is currently being monitored
dbutils.widgets.text(
    "table_name_under_monitor", "<catalog_name>.monitoring.<table_name>", label="Full (three-Level) table name"
)


# Metrics to be used for threshold violation check
# Column name in monitoring table
dbutils.widgets.text(
    "metric_to_monitor", metrics, label="Metric to be monitored for threshold violation"
) 

# Metrics to be used for threshold violation check
# Simple metric name
dbutils.widgets.text(
    "metric_name", metrics, label="Metric name to be monitored for threshold violation"
) 

# Threshold value to be checked
dbutils.widgets.text(
    "metric_violation_threshold", thresholds, label="Threshold value for metric violation"
)

# Should metric value be higher than threshold
dbutils.widgets.text(
    "is_greater_good", "True", label="Should metric value be higher than threshold"
)


# Threshold value to be checked
dbutils.widgets.text(
    "num_evaluation_windows", "5", label="Number of windows to check for violation"
)

# Threshold value to be checked
dbutils.widgets.text(
    "num_violation_windows", "2", label="Number of windows that need to violate the threshold"
)

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.28.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

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

# Get the widget values
table_name_under_monitor = dbutils.widgets.get("table_name_under_monitor")
metrics_to_monitor = dbutils.widgets.get("metric_to_monitor").split(", ")
metric_names = dbutils.widgets.get("metric_name").split(", ")
is_greater_good = dbutils.widgets.get("is_greater_good").split(", ")
metric_violation_thresholds = dbutils.widgets.get("metric_violation_threshold").split(", ")
num_evaluation_windows = dbutils.widgets.get("num_evaluation_windows")
num_violation_windows = dbutils.widgets.get("num_violation_windows")

# Assertions to ensure the variables are correctly set
assert table_name_under_monitor, "table_name_under_monitor is required"
assert metrics_to_monitor, "metrics_to_monitor is required"
assert metric_names, "metric_names is required"
assert is_greater_good, "is_greater_good is required"
assert metric_violation_thresholds, "metric_violation_thresholds is required"
assert num_evaluation_windows.isdigit(), "num_evaluation_windows must be a number"
assert num_violation_windows.isdigit(), "num_violation_windows must be a number"

# Ensure the number of metrics matches the number of thresholds
assert len(metrics_to_monitor) == len(metric_violation_thresholds), "Number of metrics must match number of thresholds"
assert len(metrics_to_monitor) == len(metric_names), "Number of metrics must match number of metric names"

# COMMAND ----------

import time
from pprint import pprint
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import MonitorInferenceLog, MonitorInferenceLogProblemType, MonitorNotifications, MonitorDestination, MonitorCronSchedule, MonitorInfoStatus, MonitorRefreshInfoState
from databricks.sdk.errors import ResourceDoesNotExist

w = WorkspaceClient()

model_monitor = w.quality_monitors.get(table_name=table_name_under_monitor)

# COMMAND ----------

eval_info_df = spark.sql(f"""
SELECT * FROM {table_name_under_monitor}
WHERE edp_load_dts = (SELECT max(edp_load_dts)
  FROM {table_name_under_monitor})
""").toPandas()

monitor_id = model_monitor.monitor_version
model_name = eval_info_df['model_name'][0]
model_version = eval_info_df['model_version'][0]
monitor_evaluation_dts = eval_info_df['edp_load_dts'][0]
env = table_name_under_monitor.split(".")[0]

# COMMAND ----------

def insert_record_to_rai_monitor_table(monitor_name, monitor_threshold, monitor_operator, monitor_current_value, is_metric_violated, monitor_category='Performance', monitor_status='Triggered'):
    insert_query = f"""
        INSERT INTO {env}.monitoring.rai_monitor_alerts 
        VALUES (
            '{monitor_id}',
            '{monitor_name}',
            '{monitor_category}',
            '',
            {monitor_threshold},
            '{monitor_evaluation_dts}',
            '{monitor_operator}',
            {monitor_current_value},
            '{monitor_status}',
            '{model_name}',
            '{model_version}',
            CURRENT_TIMESTAMP,
            '{is_metric_violated}'
        );
    """
    spark.sql(insert_query)

    print(f"Inserted record into {env}.monitoring.rai_monitor_alerts for monitor {monitor_name}")

# COMMAND ----------

from metric_violation_check_query import sql_query

def check_metric_violations():
    # Initialize a flag to track if any metric is violated
    any_metric_violated = False
    metrics_violated = ""
    metric_values = ""
    metric_thresholds = ""

    # Loop through each metric and check for violations
    for metric_to_monitor, metric_name, metric_violation_threshold, is_greater_good_metric in zip(
        metrics_to_monitor, metric_names, metric_violation_thresholds, is_greater_good
    ):
        formatted_sql_query = sql_query.format(
            table_name_under_monitor=table_name_under_monitor,
            metric_to_monitor=metric_to_monitor,
            metric_name=metric_name,
            metric_violation_threshold=metric_violation_threshold,
            num_evaluation_windows=num_evaluation_windows,
            num_violation_windows=num_violation_windows,
            is_greater_good_metric=is_greater_good_metric
        )
        # print(formatted_sql_query)
        result = spark.sql(formatted_sql_query).toPandas()
        is_metric_violated = bool(result["query_result"][0])
        metric_value = result["latest_metric_value"][0]
        print(f"Metric {metric_name} violated: {is_metric_violated}")

        if is_metric_violated:
            any_metric_violated = True
            metrics_violated += f"{metric_name},"
            metric_values += f"{metric_value},"
            metric_thresholds += f"{metric_violation_threshold},"
        monitor_operator = 'greaterThan' if is_greater_good_metric == 'True' else 'lessThan'
        insert_record_to_rai_monitor_table(metric_name, metric_violation_threshold, monitor_operator, metric_value, is_metric_violated)

    metrics_violated = metrics_violated.rstrip(',')
    metric_values = metric_values.rstrip(',')
    metric_thresholds = metric_thresholds.rstrip(',')
    
    # Set the task value to True if any metric is violated
    dbutils.jobs.taskValues.set("is_metric_violated", any_metric_violated)
    dbutils.jobs.taskValues.set("metrics_violated", metrics_violated)
    dbutils.jobs.taskValues.set("metric_values", metric_values)
    dbutils.jobs.taskValues.set("metric_thresholds", metric_thresholds)
    print(f"is_metric_violated set to {any_metric_violated}")

check_metric_violations() 
