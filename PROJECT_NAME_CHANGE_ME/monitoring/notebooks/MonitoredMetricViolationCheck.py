# Databricks notebook source
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
dbutils.widgets.text(
    "metric_to_monitor", "recall.one_vs_all[1], precision.one_vs_all[1]", label="Metric to be monitored for threshold violation"
) 

# Metrics to be used for threshold violation check
dbutils.widgets.text(
    "metric_name", "recall, precision", label="Metric name to be monitored for threshold violation"
) 

# Threshold value to be checked
dbutils.widgets.text(
    "metric_violation_threshold", "100", label="Threshold value for metric violation"
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

from metric_violation_check_query import sql_query

def check_metric_violations():
    # Get the widget values
    table_name_under_monitor = dbutils.widgets.get("table_name_under_monitor")
    metrics_to_monitor = dbutils.widgets.get("metric_to_monitor").split(", ")
    metric_names = dbutils.widgets.get("metric_name").split(", ")
    metric_violation_thresholds = dbutils.widgets.get("metric_violation_threshold").split(", ")
    num_evaluation_windows = dbutils.widgets.get("num_evaluation_windows")
    num_violation_windows = dbutils.widgets.get("num_violation_windows")

    # Assertions to ensure the variables are correctly set
    assert table_name_under_monitor, "table_name_under_monitor is required"
    assert metrics_to_monitor, "metrics_to_monitor is required"
    assert metric_names, "metric_names is required"
    assert metric_violation_thresholds, "metric_violation_thresholds is required"
    assert num_evaluation_windows.isdigit(), "num_evaluation_windows must be a number"
    assert num_violation_windows.isdigit(), "num_violation_windows must be a number"

    # Ensure the number of metrics matches the number of thresholds
    assert len(metrics_to_monitor) == len(metric_violation_thresholds), "Number of metrics must match number of thresholds"
    assert len(metrics_to_monitor) == len(metric_names), "Number of metrics must match number of metric names"

    # Initialize a flag to track if any metric is violated
    any_metric_violated = False

    # Loop through each metric and check for violations
    for metric_to_monitor, metric_name, metric_violation_threshold in zip(
        metrics_to_monitor, metric_names, metric_violation_thresholds
    ):
        formatted_sql_query = sql_query.format(
            table_name_under_monitor=table_name_under_monitor,
            metric_to_monitor=metric_to_monitor,
            metric_name=metric_name,
            metric_violation_threshold=metric_violation_threshold,
            num_evaluation_windows=num_evaluation_windows,
            num_violation_windows=num_violation_windows
        )
        # print(formatted_sql_query)
        is_metric_violated = bool(spark.sql(formatted_sql_query).toPandas()["query_result"][0])
        print(f"Metric {metric_name} violated: {is_metric_violated}")
        if is_metric_violated:
            any_metric_violated = True

    # Set the task value to True if any metric is violated
    dbutils.jobs.taskValues.set("is_metric_violated", any_metric_violated)
    print(f"is_metric_violated set to {any_metric_violated}")

check_metric_violations() 


