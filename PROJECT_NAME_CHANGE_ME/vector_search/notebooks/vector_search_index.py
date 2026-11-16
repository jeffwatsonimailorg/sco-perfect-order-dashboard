# Databricks notebook source
# MAGIC %load_ext autoreload
# MAGIC %autoreload 2

# COMMAND ----------

import os
notebook_path =  '/Workspace/' + os.path.dirname(dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get())
%cd $notebook_path

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch==0.56

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# Notebook Environment
dbutils.widgets.dropdown(
    "env", 
    "dev", ["dev", "staging", "prod"], 
    label="Environment Name"
    )

# Catalog Name suffix
dbutils.widgets.text(
    "catalog_name",
    "data_science",
    label="Catalog Name",
)

# Schema name for UC table/volume/index etc.
dbutils.widgets.text(
    "schema_name",
    "ds_output",
    label="Schema Name",
)
# COMMAND ----------

env = dbutils.widgets.get("env")
catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")

assert env, "Environment name is required"
assert catalog_name, "Catalog name is required"
assert schema_name, "Schema name is required"

# Source table containing document chunks
dbutils.widgets.text(
    "source_table_name",
    f"{env}_{catalog_name}.{schema_name}.PROJECT_NAME_CHANGE_ME_chunk",
    label="Source Table Name",
)

# Vector Search endpoint compute name
dbutils.widgets.text(
    "endpoint_name",
    f"{env}-PROJECT_NAME_CHANGE_ME",
    label="Vector Search Endpoint",
)

# Vector Search index name
dbutils.widgets.text(
    "vs_index",
    "PROJECT_NAME_CHANGE_ME_index",
    label="Vector Search Index",
)

# Embedding model endpoint name
dbutils.widgets.text(
    "embedding_model_endpoint",
    # TODO: Update to your embedding model endpoint name
    "bge-large-v1_5", 
    label="Embedding Model Endpoint",
)

# Pipeline type for Vector Search index
dbutils.widgets.dropdown(
    "pipeline_type",
    "TRIGGERED", ["TRIGGERED", "CONTINUOUS"], 
    label="Pipeline Type",
)

# Primary Key of the source table
dbutils.widgets.text(
    "primary_key",
    # TODO: Update to your primary_key column name
    "id", 
    label="Primary Key Column Name",
)

# Column from source table you want to create embeddings on
dbutils.widgets.text(
    "embedding_source_column",
    # TODO: Update to your embedding source column name
    "page_content", 
    label="Embedding Source Column Name",
)


# COMMAND ----------
from databricks.vector_search.client import VectorSearchClient
import datetime


def create_endpoint(client, endpoint_name):
    try:
        if client.get_endpoint(name=endpoint_name):
            print(f"Endpoint '{endpoint_name}' already exists.")
            return
    except Exception:
        # If get_endpoint raises an exception, assume endpoint does not exist and create it
        try:
            client.create_endpoint(name=endpoint_name, endpoint_type="STANDARD")
            client.wait_for_endpoint(name=endpoint_name, verbose=True, timeout=datetime.timedelta(seconds=3600))
            print(f"Waiting for endpoint '{endpoint_name}' to be ready...")
        except Exception as e:
            print(f"Error creating endpoint '{endpoint_name}': {e}")


client = VectorSearchClient(disable_notice=True)


# COMMAND ----------

source_table_name = dbutils.widgets.get("source_table_name")
endpoint_name = dbutils.widgets.get("endpoint_name")
embedding_model_endpoint = dbutils.widgets.get("embedding_model_endpoint")
vs_index = dbutils.widgets.get("vs_index")
vs_index_fullname = f"{env}_{catalog_name}.{schema_name}.{vs_index}"
pipeline_type = dbutils.widgets.get("pipeline_type")
primary_key = dbutils.widgets.get("primary_key")
embedding_source_column = dbutils.widgets.get("embedding_source_column")

assert source_table_name, "Source table name is required"
assert endpoint_name, "Vector Search endpoint name is required"
assert embedding_model_endpoint, "Embedding model endpoint name is required"
assert vs_index, "Vector Search index name is required"
assert pipeline_type, "Pipeline type is required"
assert primary_key, "Primary key column name is required"
assert embedding_source_column, "Embedding source column name is required"

# COMMAND ----------

create_endpoint(client, endpoint_name)

# COMMAND ----------

index = client.create_delta_sync_index(
    endpoint_name=endpoint_name,
    source_table_name=source_table_name,
    index_name=vs_index_fullname,
    pipeline_type=pipeline_type,
    primary_key=primary_key,
    # TODO: select columns to sync with vector search index. If left blank, all columns will be synced.
    # columns_to_sync=[
    #     "id",
    #     "col2",
    #     "col3",
    # ],
    sync_computed_embeddings=True,
    embedding_source_column=embedding_source_column,
    embedding_model_endpoint_name=embedding_model_endpoint,
)
index.describe()["status"]["message"]
