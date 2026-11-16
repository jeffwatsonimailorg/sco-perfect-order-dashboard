# Databricks notebook source
# Notebook Environment
dbutils.widgets.dropdown("env", "dev_datascience", ["dev_datascience", "staging_datascience", "prod_datascience"], "Environment Name")
env = dbutils.widgets.get("env")
if not env.endswith("_datascience"):
    env = f"{env}_datascience"

# Delta table to store the output predictions.
dbutils.widgets.text("output_table_name", f"{env}.monitoring.<TABLE_NAME>", label="Output Table Name"
)

# COMMAND ----------

import sys
import os
notebook_path =  '/Workspace/' + os.path.dirname(dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get())
%cd $notebook_path

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.functions import *
import pyspark.sql.functions as F
from pyspark.sql.types import StringType, IntegerType, DateType, LongType, TimestampType
import re
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, array, struct, array_distinct
from pyspark.sql.window import Window
from pyspark.sql.functions import when, col, collect_list
from pyspark.sql.functions import pandas_udf, PandasUDFType
from pyspark.sql.functions import max

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
from pyspark.sql.functions import col, current_date, date_add

# COMMAND ----------

env = dbutils.widgets.get("env")
if not env.endswith("_datascience"):
    env = f"{env}_datascience"

output_table_name = dbutils.widgets.get("output_table_name")

# COMMAND ----------

# Check the prediction table exists
def table_exists(catalog_name, schema_name, table_name):
    try:
        # Switch to the specified catalog
        spark.sql(f"USE CATALOG {catalog_name}")   
        print(f"Using catalog: {catalog_name}")  
        # List all tables in the specified schema
        tables = spark.sql(f"SHOW TABLES IN {schema_name}").toPandas()
        # Check if the table is present
        if table_name in tables['tableName'].values:
            print("Table is present")
            # load the tables from source and prediction table schema
            df = spark.table(f"{catalog_name}.{schema_name}.{table_name}")
            timestamp_col = "edp_load_dts"
            max_date_row = df.select(max(col(timestamp_col))).collect()[0][0]

            #CHANGEME: change query to UPDATE table
            df_new = spark.sql(f"""
                SELECT *
                FROM "{env}.ds_output.<OUTPUT_TABLE>"
                WHERE {timestamp_col} > '{max_date_row}';
            """)

            df_new.write.mode("append").option("mergeSchema", "true").saveAsTable(f"{catalog_name}.{schema_name}.{table_name}")
            print("Done, rows added to table")
            return df_new
        else:
            print(f"Table not present. Created from {env}.ds_output.<OUTPUT_TABLE>")
            #CHANGEME: change query to CREATE table
            df_new = spark.sql(f"""
                SELECT *
                FROM "{env}.ds_output.<OUTPUT_TABLE>";
            """)

            df_new.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(f"{catalog_name}.{schema_name}.{table_name}")
            print("created table")

            #CHANGEME: change query to GRANT table permissions to users 
            if catalog_name == 'dev_datascience':
                spark.sql(f"GRANT SELECT ON TABLE {catalog_name}.{schema_name}.{table_name} TO DPG_MLOPS_SP_MANAGE_DEV")
            elif catalog_name == 'prod_datascience':
                spark.sql(f"GRANT SELECT ON TABLE {catalog_name}.{schema_name}.{table_name} TO DPG_MLOPS_SP_MANAGE_PRD")
            else:
                spark.sql(f"GRANT SELECT ON TABLE {catalog_name}.{schema_name}.{table_name} TO DPG_MLOPS_SP_MANAGE_TST")

            spark.sql(f"GRANT MANAGE ON TABLE {catalog_name}.{schema_name}.{table_name} TO DP_DAP_MLOPS_USR")
            return df_new
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


# COMMAND ----------

output_table_name_short = output_table_name.split('.')[-1]
df_inference = table_exists(env, 'monitoring', output_table_name_short)
display(df_inference)
