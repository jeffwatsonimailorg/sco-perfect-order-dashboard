# Required fields 
CATALOG = "" # Change this to your catalog name (e.g., "prod_datascience")
SCHEMA = "monitoring" 
SHORT_MODEL_NAME = "" # AKA project name
TABLE_NAME = f"{CATALOG}.{SCHEMA}.{SHORT_MODEL_NAME}_inference" # Assuming this is the table name for the inference and ground truth data.
ASSETS_DIR = "/MLOps/databricks_lakehouse_monitoring"
OUTPUT_SCHEMA_NAME = f"{CATALOG}.{SCHEMA}"

# Optional fields
# Inference Log
GRANULARITIES = ["<interval>"] # List of granularities to monitor (e.g., ["1 day", "1 week", "1 month"])
MODEL_ID_COL =  "<model_id_column>" # (e.g., "model_version")
PREDICTION_COL = "<prediction_column_name>"
LABEL_COL = "<ground_truth_column_name>"
PROBLEM_TYPE = "<PROBLEM_TYPE_REGRESSION_OR_CLASSIFICATION>" # Choose PROBLEM_TYPE_REGRESSION or PROBLEM_TYPE_CLASSIFICATION
TIMESTAMP_COL = "<timestamp_column_name>" # (e.g., "edp_load_dts")

# Notifications
EMAIL_ADDRESSES = ["first.last@imail.org","first2.last2@imail.org"] # List of email addresses to send notifications to

# Schedule
QUARTZ_CRON_EXPRESSION = "0 0 8 * * ?" # Run Every day at 8am
TIMEZONE_ID = "America/Denver"