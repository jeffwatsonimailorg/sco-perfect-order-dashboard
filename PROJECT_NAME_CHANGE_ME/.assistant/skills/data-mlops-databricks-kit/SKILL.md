---
name: data-mlops-databricks-kit
description: >
  Template and architecture guide for building production MLOps projects on Databricks
  using Unity Catalog, Feature Store, MLflow, and Declarative Automation Bundles (DABs).
  Read this skill when the user asks to scaffold a new ML project, create a regression
  or classification training pipeline, set up feature engineering with Feature Store,
  configure model validation and deployment, build batch inference pipelines, set up
  model monitoring with Lakehouse Monitoring, configure retraining triggers, create
  DABs resource YAML files for ML workflows, or extend an existing project following
  this repo's conventions.
---

# data-mlops-databricks-kit

This skill encodes the conventions, folder structure, code patterns, and DABs resource
templates from the `template-data-mlops-databricks-kit` repo. All examples below use
placeholder names (`PROJECT_NAME`, `MODEL_NAME`, etc.) — substitute the user's actual
project and model names when generating code.

---

## 1. Project Structure

Every ML project follows this directory layout under the bundle root:

```
PROJECT_NAME/
├── databricks.yml                          # Bundle config: variables, targets, permissions, resources
├── requirements.txt                        # Python deps (mlflow, sklearn, lightgbm, pandas, etc.)
├── pytest.ini                              # Test config
├── __init__.py
├── training/
│   └── notebooks/
│       └── TrainWithFeatureStore           # Training notebook (or Train for non-FS)
├── validation/
│   ├── notebooks/
│   │   └── ModelValidation                 # Validation gate notebook
│   └── validation.py                       # Custom metrics + thresholds
├── deployment/
│   ├── model_deployment/
│   │   ├── notebooks/
│   │   │   └── ModelDeployment             # Alias promotion notebook
│   │   └── deploy.py                       # Champion/challenger alias logic
│   └── batch_inference/
│       ├── notebooks/
│       │   └── BatchInference              # Batch scoring notebook
│       ├── predict.py                      # Inference logic (FS score_batch or mlflow.pyfunc)
│       └── README.md
├── monitoring/
│   ├── notebooks/
│   │   ├── CreateMonitor                   # Lakehouse Monitor setup
│   │   ├── MonitoredMetricViolationCheck   # Metric drift detection
│   │   ├── EmailAlert                      # Alert notification
│   │   └── feedback                        # Ground-truth feedback loop
│   ├── config.py                           # Monitor config (granularity, columns, problem type)
│   ├── metric_violation_check_query.py     # Metric violation query logic
│   └── dashboard/
│       ├── Template Regression Monitoring.json
│       └── Template Classification Monitoring.json
├── sql/
│   ├── create-monitoring-table.sql
│   ├── update-monitoring-table.sql
│   └── grant-permissions.sql
├── resources/
│   ├── model-workflow-resource.yml         # Train → Validate → Deploy job
│   ├── batch-inference-workflow-resource.yml
│   ├── monitoring-resource.yml             # Monitor + metric refresh jobs
│   ├── retraining-resource.yml             # Auto-retrain on metric violation
│   └── dashboard_monitoring.yml
└── tests/
    └── training/
        └── test_notebooks.py
```

---

## 2. databricks.yml — Bundle Configuration

The root bundle config defines variables, permissions, registered models, experiments,
resource includes, and multi-environment targets.

### Template

```yaml
bundle:
  name: PROJECT_NAME

workspace:
  root_path: /Workspace/MLOps/bundles/${bundle.name}/envs/${bundle.target}

variables:
  catalog_name:
    description: Unity Catalog catalog for all output
    default: dev_CATALOG
  experiment_name:
    description: Experiment name for model logging + evaluation
    default: /MLOps/experiments/${bundle.target}-${bundle.name}-experiment
  model_name:
    description: Short model name (used in registered_models and jobs)
    default: PROJECT_NAME
  id_group_name:
    description: Managed identity group for permissions
    default: DPG_SP_GH_DATA_MLOPS_PROJECT_NAME_DEV

permissions:
  - level: CAN_VIEW
    group_name: users
  - level: CAN_MANAGE
    group_name: ${var.id_group_name}

resources:
  registered_models:
    model:
      name: ${var.model_name}-model
      catalog_name: ${var.catalog_name}
      schema_name: ds_output
      comment: >-
        Registered model in Unity Catalog for the PROJECT_NAME ML project
        for ${bundle.target} deployment target.
      grants:
        - privileges:
            - EXECUTE
          principal: account users

  experiments:
    experiment:
      name: ${var.experiment_name}

include:
  - ./resources/model-workflow-resource.yml
  # - ./resources/batch-inference-workflow-resource.yml
  # - ./resources/monitoring-resource.yml
  # - ./resources/retraining-resource.yml

targets:
  dev:
    default: true
    variables:
      catalog_name: dev_CATALOG
      id_group_name: DPG_SP_GH_DATA_MLOPS_PROJECT_NAME_DEV
    workspace:
      host: https://adb-XXXXX.XX.azuredatabricks.net

  test:
    variables:
      catalog_name: test_CATALOG
      id_group_name: DPG_SP_GH_DATA_MLOPS_PROJECT_NAME_TST
    workspace:
      host: https://adb-YYYYY.YY.azuredatabricks.net

  prod:
    variables:
      catalog_name: prod_CATALOG
      id_group_name: DPG_SP_GH_DATA_MLOPS_PROJECT_NAME_PRD
    workspace:
      host: https://adb-ZZZZZ.ZZ.azuredatabricks.net
    resources:
      jobs:
        model_training_job:
          schedule:
            quartz_cron_expression: "0 0 18 * * ?"
            timezone_id: America/Denver
```

### Key conventions

- **Variable substitution**: Always reference `${var.catalog_name}`, `${bundle.target}`,
  `${bundle.name}` — never hardcode environment-specific values.
- **Three-level model name**: `${var.catalog_name}.ds_output.${var.model_name}-model`.
- **Permissions**: Every bundle must have `CAN_VIEW` for `users` and `CAN_MANAGE` for
  the project's managed identity group.
- **Targets**: Always provide `dev` (default: true), `test`, and `prod` with
  per-environment overrides for `catalog_name`, `id_group_name`, and `workspace.host`.

---

## 3. Training Notebook Patterns

Every training notebook follows this structure:

### 3.1 Common Notebook Preamble

```python
# Cell 1: Header comment with parameter documentation
# Cell 2: autoreload
%load_ext autoreload
%autoreload 2

# Cell 3: Set working directory
import os
notebook_path = '/Workspace/' + os.path.dirname(
    dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
)
%cd $notebook_path

# Cell 4: Install dependencies
%pip install -r ../../requirements.txt

# Cell 5: Restart Python after pip install
dbutils.library.restartPython()
```

### 3.2 Widget Parameters

```python
dbutils.widgets.dropdown("env", "staging", ["staging", "prod"], "Environment Name")
dbutils.widgets.text("training_data_path", "<default_path>", label="Path to the training data")
dbutils.widgets.text("experiment_name", "/dev-PROJECT_NAME-experiment", label="MLflow experiment name")
dbutils.widgets.text("model_name", "dev_CATALOG.ds_output.PROJECT_NAME-model", label="Full (Three-Level) Model Name")
```

### 3.3 Regression Training (with Feature Store)

Use when: predicting a continuous numeric target (e.g., fare_amount, price, duration).

```python
import mlflow
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup

# Setup
mlflow.set_experiment(experiment_name)
mlflow.set_registry_uri('databricks-uc')
fe = FeatureEngineeringClient()

# Load raw data
raw_data = spark.read.format("delta").load(input_table_path)
# OR: raw_data = spark.table("catalog.schema.table_name")

# Feature lookups (point-in-time join)
pickup_feature_lookups = [
    FeatureLookup(
        table_name="catalog.schema.pickup_features",
        feature_names=["mean_fare_window_1h_pickup_zip", "count_trips_window_1h_pickup_zip"],
        lookup_key=["pickup_zip"],
        timestamp_lookup_key=["rounded_pickup_datetime"],  # for point-in-time
    ),
]

# Create training set
mlflow.end_run()  # end any existing run
mlflow.start_run()

training_set = fe.create_training_set(
    df=taxi_data,
    feature_lookups=pickup_feature_lookups + dropoff_feature_lookups,
    label="fare_amount",
    exclude_columns=["rounded_pickup_datetime", "rounded_dropoff_datetime"],
)
training_df = training_set.load_df()

# Train
data = training_df.toPandas()[features_and_label]
train, test = train_test_split(data, random_state=123)
X_train = train.drop(["fare_amount"], axis=1)
y_train = train.fare_amount

mlflow.lightgbm.autolog()
train_lgb_dataset = lgb.Dataset(X_train, label=y_train.values)
param = {"num_leaves": 32, "objective": "regression", "metric": "rmse"}
model = lgb.train(param, train_lgb_dataset, num_rounds=100)

# Log with Feature Store
fe.log_model(
    model=model,
    artifact_path="model_packaged",
    flavor=mlflow.lightgbm,
    training_set=training_set,
    registered_model_name=model_name,
)
```

### 3.4 Classification Training (with Feature Store)

Use when: predicting a categorical target (e.g., fraud/not-fraud, churn, category labels).

```python
import mlflow
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup

# Setup (same preamble as regression)
mlflow.set_experiment(experiment_name)
mlflow.set_registry_uri('databricks-uc')
fe = FeatureEngineeringClient()

# Load and prepare data
raw_data = spark.table("catalog.schema.source_table")

# Feature lookups
feature_lookups = [
    FeatureLookup(
        table_name="catalog.schema.feature_table",
        feature_names=["feature_1", "feature_2", "feature_3"],
        lookup_key=["entity_id"],
    ),
]

# Create training set
mlflow.end_run()
mlflow.start_run()

training_set = fe.create_training_set(
    df=raw_data,
    feature_lookups=feature_lookups,
    label="target_column",
    exclude_columns=["columns_to_exclude"],
)
training_df = training_set.load_df()

# Train
data = training_df.toPandas()
train, test = train_test_split(data, random_state=123, stratify=data["target_column"])
X_train = train.drop(["target_column"], axis=1)
y_train = train["target_column"]
X_test = test.drop(["target_column"], axis=1)
y_test = test["target_column"]

mlflow.lightgbm.autolog()
train_lgb_dataset = lgb.Dataset(X_train, label=y_train.values)
test_lgb_dataset = lgb.Dataset(X_test, label=y_test.values)

param = {
    "num_leaves": 32,
    "objective": "binary",       # or "multiclass" + "num_class": N
    "metric": "binary_logloss",  # or "multi_logloss"
}
model = lgb.train(param, train_lgb_dataset, num_rounds=100, valid_sets=[test_lgb_dataset])

# Evaluate
y_pred = (model.predict(X_test) > 0.5).astype(int)  # for binary
mlflow.log_metrics({
    "accuracy": accuracy_score(y_test, y_pred),
    "f1": f1_score(y_test, y_pred, average="weighted"),
    "precision": precision_score(y_test, y_pred, average="weighted"),
    "recall": recall_score(y_test, y_pred, average="weighted"),
})

# Log with Feature Store
fe.log_model(
    model=model,
    artifact_path="model_packaged",
    flavor=mlflow.lightgbm,
    training_set=training_set,
    registered_model_name=model_name,
)
```

### 3.5 Training Without Feature Store

When Feature Store is not needed, use standard MLflow logging:

```python
import mlflow
from sklearn.ensemble import RandomForestClassifier  # or RandomForestRegressor
from sklearn.model_selection import train_test_split

mlflow.set_experiment(experiment_name)
mlflow.set_registry_uri('databricks-uc')

raw_data = spark.table("catalog.schema.table").toPandas()
train, test = train_test_split(raw_data, random_state=123)

X_train = train.drop(["target"], axis=1)
y_train = train["target"]

with mlflow.start_run():
    mlflow.sklearn.autolog()
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Log and register
    mlflow.sklearn.log_model(
        model,
        artifact_path="model",
        registered_model_name=model_name,
    )
```

### 3.6 Task Value Output (end of every training notebook)

Always output task values so downstream tasks can consume them:

```python
from mlflow.tracking import MlflowClient

def get_latest_model_version(model_name):
    client = MlflowClient()
    latest_version = 1
    for mv in client.search_model_versions(f"name='{model_name}'"):
        version_int = int(mv.version)
        if version_int > latest_version:
            latest_version = version_int
    return latest_version

model_version = get_latest_model_version(model_name)
model_uri = f"models:/{model_name}/{model_version}"
dbutils.jobs.taskValues.set("model_uri", model_uri)
dbutils.jobs.taskValues.set("model_name", model_name)
dbutils.jobs.taskValues.set("model_version", model_version)
dbutils.notebook.exit(model_uri)
```

---

## 4. Model Validation

### 4.1 validation.py — Custom Metrics and Thresholds

#### Regression

```python
import numpy as np
from mlflow.models import make_metric, MetricThreshold

def custom_metrics():
    def squared_diff_plus_one(eval_df, _builtin_metrics):
        return np.sum(np.abs(eval_df["prediction"] - eval_df["target"] + 1) ** 2)
    return [make_metric(eval_fn=squared_diff_plus_one, greater_is_better=False)]

def validation_thresholds():
    return {
        "max_error": MetricThreshold(threshold=500, greater_is_better=False),
        "mean_squared_error": MetricThreshold(threshold=500, greater_is_better=False),
    }

def evaluator_config():
    return {}
```

#### Classification

```python
from mlflow.models import MetricThreshold

def custom_metrics():
    return []  # Built-in classification metrics are usually sufficient

def validation_thresholds():
    return {
        "accuracy_score": MetricThreshold(threshold=0.70, greater_is_better=True),
        "f1_score": MetricThreshold(threshold=0.65, greater_is_better=True),
        "precision_score": MetricThreshold(threshold=0.60, greater_is_better=True),
        "recall_score": MetricThreshold(threshold=0.60, greater_is_better=True),
    }

def evaluator_config():
    return {}
```

### 4.2 ModelValidation Notebook

The validation notebook reads task values from the Train task, loads the model,
runs `mlflow.evaluate()`, checks thresholds, and promotes to champion on success.

Key parameters:
- `run_mode`: `disabled` | `dry_run` | `enabled`
- `enable_baseline_comparison`: `true` | `false`
- `model_type`: `regressor` | `classifier`
- `targets`: label column name
- `validation_input`: SQL query for validation data

Promotion logic: On success, set alias to `champion` using:
```python
from mlflow.tracking import MlflowClient
client = MlflowClient(registry_uri="databricks-uc")
client.set_registered_model_alias(name=model_name, alias="champion", version=model_version)
```

---

## 5. Model Deployment

### 5.1 deploy.py — Champion Alias Promotion

```python
from mlflow.tracking import MlflowClient

def deploy(model_uri, env):
    _, model_name, version = model_uri.split("/")
    client = MlflowClient(registry_uri="databricks-uc")
    mv = client.get_model_version(model_name, version)
    target_alias = "champion"
    if target_alias not in mv.aliases:
        client.set_registered_model_alias(name=model_name, alias=target_alias, version=version)
        if target_alias == "champion" and "challenger" in mv.aliases:
            client.delete_registered_model_alias(name=model_name, alias="challenger")
```

### 5.2 Challenger / Champion Pattern

During training, set alias to `challenger`:
```python
client.set_registered_model_alias(name=model_name, alias="challenger", version=model_version)
```

After validation passes, promote to `champion` (deploy.py handles this).

For batch inference, always load the `champion` alias:
```python
alias = "champion"
model_uri = f"models:/{model_name}@{alias}"
```

---

## 6. Batch Inference

### 6.1 predict.py

```python
import mlflow
from pyspark.sql.functions import struct, lit, to_timestamp

def predict_batch(spark_session, model_uri, input_table_name, output_table_name, model_version, ts):
    mlflow.set_registry_uri("databricks-uc")
    table = spark_session.table(input_table_name)

    # With Feature Store:
    from databricks.feature_engineering import FeatureEngineeringClient
    fe_client = FeatureEngineeringClient()
    prediction_df = fe_client.score_batch(model_uri=model_uri, df=table)

    # Without Feature Store:
    # loaded_model = mlflow.pyfunc.load_model(model_uri)
    # prediction_df = loaded_model.predict(table.toPandas())

    output_df = (
        prediction_df
        .withColumn("prediction", prediction_df["prediction"])
        .withColumn("model_version", lit(model_version))
        .withColumn("inference_timestamp", to_timestamp(lit(ts)))
    )
    output_df.write.format("delta").mode("overwrite").saveAsTable(output_table_name)
```

---

## 7. Monitoring

### 7.1 config.py — Monitor Configuration

```python
# Adjust these for your model
GRANULARITIES = ["1 day"]       # or ["1 week"], ["1 month"]
MODEL_ID_COL = "model_version"
PREDICTION_COL = "prediction"
LABEL_COL = "label"             # ground truth column
PROBLEM_TYPE = "PROBLEM_TYPE_CLASSIFICATION"  # or PROBLEM_TYPE_REGRESSION
TIMESTAMP_COL = "inference_timestamp"

EMAIL_ADDRESSES = ["mlops-support@imail.org"]
QUARTZ_CRON_EXPRESSION = "0 0 8 * * ?"  # Daily at 8am
TIMEZONE_ID = "America/Denver"
```

### 7.2 Lakehouse Monitor Creation

Uses `databricks-sdk` `WorkspaceClient().quality_monitors`:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import (
    MonitorInferenceLog, MonitorInferenceLogProblemType,
    MonitorNotifications, MonitorDestination, MonitorCronSchedule,
)

w = WorkspaceClient()
w.quality_monitors.create(
    table_name=TABLE_NAME,
    output_schema_name=OUTPUT_SCHEMA_NAME,
    inference_log=MonitorInferenceLog(
        granularities=GRANULARITIES,
        model_id_col=MODEL_ID_COL,
        prediction_col=PREDICTION_COL,
        label_col=LABEL_COL,
        problem_type=MonitorInferenceLogProblemType[PROBLEM_TYPE],
        timestamp_col=TIMESTAMP_COL,
    ),
    notifications=MonitorNotifications(
        on_new_classification_tag_detected=MonitorDestination(email_addresses=EMAIL_ADDRESSES),
    ),
    schedule=MonitorCronSchedule(
        quartz_cron_expression=QUARTZ_CRON_EXPRESSION,
        timezone_id=TIMEZONE_ID,
    ),
)
```

### 7.3 Custom Monitor Metrics

```python
from databricks.sdk.service.catalog import MonitorMetric, MonitorMetricType
from pyspark.sql import types as T

CUSTOM_METRICS = [
    MonitorMetric(
        type=MonitorMetricType.CUSTOM_METRIC_TYPE_AGGREGATE,
        name="accuracy",
        input_columns=[":table"],
        definition=f"AVG(CASE WHEN {PREDICTION_COL} = {LABEL_COL} THEN 1 ELSE 0 END)",
        output_data_type=T.StructField("accuracy", T.DoubleType()).json(),
    ),
]
```

### 7.4 Metric Violation Check and Retraining Trigger

The retraining pipeline checks metric tables for threshold violations:
- Configurable via `metric_to_monitor`, `metric_violation_threshold`, `num_evaluation_windows`
- On violation: triggers `model_training_job` via `run_job_task`
- Sends email alert via `EmailAlert` notebook

---

## 8. DABs Resource YAML Templates

### 8.1 Cluster Anchor (reuse across jobs)

```yaml
# Single node cluster
new_cluster: &new_cluster
  new_cluster:
    spark_version: 16.4.x-scala2.13
    node_type_id: Standard_D4ds_v6
    driver_node_type_id: Standard_D4ds_v6
    num_workers: 0
    spark_conf:
      spark.databricks.cluster.profile: "singleNode"
      spark.master: local[*]
    data_security_mode: "SINGLE_USER"
    custom_tags:
      Department: MLOps
      ResourceClass: SingleNode

# Multi node cluster (uncomment when needed)
# new_cluster: &new_cluster
#   new_cluster:
#     spark_version: 16.4.x-scala2.13
#     node_type_id: Standard_D4ds_v6
#     driver_node_type_id: Standard_D4ds_v6
#     autoscale:
#       min_workers: 1
#       max_workers: 8
#     data_security_mode: "SINGLE_USER"
```

### 8.2 model-workflow-resource.yml (Train → Validate → Deploy)

```yaml
resources:
  jobs:
    model_training_job:
      name: mlops_${bundle.target}-PROJECT_NAME-model-training-job
      tasks:
        - task_key: Train
          notebook_task:
            notebook_path: ../training/notebooks/TrainWithFeatureStore.py
            base_parameters:
              env: ${bundle.target}
              experiment_name: ${var.experiment_name}
              model_name: ${var.catalog_name}.ds_output.${var.model_name}-model
              git_source_info: url:${bundle.git.origin_url}; branch:${bundle.git.branch}; commit:${bundle.git.commit}

        - task_key: ModelValidation
          depends_on:
            - task_key: Train
          notebook_task:
            notebook_path: ../validation/notebooks/ModelValidation.py
            base_parameters:
              env: ${bundle.target}
              run_mode: dry_run
              enable_baseline_comparison: "false"
              validation_input: >-
                SELECT * FROM ${var.catalog_name}.ds_output.validation_data LIMIT 1000
              model_type: regressor  # or classifier
              targets: target_column
              git_source_info: url:${bundle.git.origin_url}; branch:${bundle.git.branch}; commit:${bundle.git.commit}

        - task_key: ModelDeployment
          depends_on:
            - task_key: ModelValidation
          notebook_task:
            notebook_path: ../deployment/model_deployment/notebooks/ModelDeployment.py
            base_parameters:
              env: ${bundle.target}
              git_source_info: url:${bundle.git.origin_url}; branch:${bundle.git.branch}; commit:${bundle.git.commit}

      email_notifications:
        on_failure:
          - mlops-support@imail.org
      tags:
        Department: MLOps
        model_name: ${bundle.name}
```

### 8.3 batch-inference-workflow-resource.yml

```yaml
resources:
  jobs:
    batch_inference_job:
      name: mlops_${bundle.target}-PROJECT_NAME-batch-inference-job
      job_clusters:
        - job_cluster_key: batch_inference_job_cluster
          <<: *new_cluster
      tasks:
        - task_key: batch_inference_job
          job_cluster_key: batch_inference_job_cluster
          notebook_task:
            notebook_path: ../deployment/batch_inference/notebooks/BatchInference.py
            base_parameters:
              env: ${bundle.target}
              input_table_name: ${var.catalog_name}.ds_output.inference_input
              output_table_name: ${var.catalog_name}.ds_output.predictions
              model_name: ${var.catalog_name}.ds_output.${var.model_name}-model
              git_source_info: url:${bundle.git.origin_url}; branch:${bundle.git.branch}; commit:${bundle.git.commit}
      email_notifications:
        on_failure:
          - mlops-support@imail.org
      tags:
        Department: MLOps
        model_name: ${bundle.name}
```

### 8.4 retraining-resource.yml (Metric Violation → Retrain)

```yaml
resources:
  jobs:
    retraining_job:
      name: mlops_${bundle.target}-PROJECT_NAME-monitoring-retraining-job
      job_clusters:
        - job_cluster_key: retraining_job_cluster
          <<: *new_cluster
      tasks:
        - task_key: monitored_metric_violation_check
          job_cluster_key: retraining_job_cluster
          notebook_task:
            notebook_path: ../monitoring/notebooks/MonitoredMetricViolationCheck.py
            base_parameters:
              env: ${bundle.target}
              table_name_under_monitor: ${var.catalog_name}.monitoring.PROJECT_NAME_inference
              metric_to_monitor: recall.one_vs_all[1], precision.one_vs_all[1]
              metric_name: recall, precision
              metric_violation_threshold: "0.70, 0.60"
              is_greater_good: "True, True"
              num_evaluation_windows: 5
              num_violation_windows: 2
              git_source_info: url:${bundle.git.origin_url}; branch:${bundle.git.branch}; commit:${bundle.git.commit}

        - task_key: is_metric_violated
          depends_on:
            - task_key: monitored_metric_violation_check
          condition_task:
            op: EQUAL_TO
            left: "{{tasks.monitored_metric_violation_check.values.is_metric_violated}}"
            right: "true"

        - task_key: send_alert_email
          depends_on:
            - task_key: is_metric_violated
              outcome: "true"
          notebook_task:
            notebook_path: ../monitoring/notebooks/EmailAlert.py
            base_parameters:
              env: ${bundle.target}
              metrics_violated: "{{tasks.monitored_metric_violation_check.values.metrics_violated}}"
              metric_values: "{{tasks.monitored_metric_violation_check.values.metric_values}}"
              metric_thresholds: "{{tasks.monitored_metric_violation_check.values.metric_thresholds}}"

        - task_key: trigger_retraining
          depends_on:
            - task_key: is_metric_violated
              outcome: "true"
          run_job_task:
            job_id: ${resources.jobs.model_training_job.id}

      schedule:
        quartz_cron_expression: "0 0 18 1 * ?"
        timezone_id: America/Denver
      email_notifications:
        on_failure:
          - mlops-support@imail.org
      tags:
        Department: MLOps
```

### 8.5 monitoring-resource.yml

```yaml
resources:
  jobs:
    create_monitor_table_job:
      name: mlops_${bundle.target}-PROJECT_NAME-create-monitoring-table
      tasks:
        - task_key: create_monitoring_table
          notebook_task:
            notebook_path: ../monitoring/notebooks/feedback.py
            base_parameters:
              env: ${bundle.target}
              output_table_name: ${var.catalog_name}.monitoring.MONITORING_TABLE
              git_source_info: url:${bundle.git.origin_url}; branch:${bundle.git.branch}; commit:${bundle.git.commit}
      schedule:
        quartz_cron_expression: "0 0 9 1 * ?"
        timezone_id: America/Denver
      tags:
        Department: MLOps
      email_notifications:
        on_failure:
          - mlops-support@imail.org

    create_monitor_job:
      name: mlops_${bundle.target}-PROJECT_NAME-create-monitor-job
      tasks:
        - task_key: create_monitor
          notebook_task:
            notebook_path: ../monitoring/notebooks/CreateMonitor.py
            base_parameters:
              CATALOG: ${var.catalog_name}
              SCHEMA: monitoring
              SHORT_MODEL_NAME: MODEL_NAME
              ASSETS_DIR: /MLOps/databricks_lakehouse_monitoring
              git_source_info: url:${bundle.git.origin_url}; branch:${bundle.git.branch}; commit:${bundle.git.commit}
      schedule:
        quartz_cron_expression: "0 30 9 1 * ?"
        timezone_id: America/Denver
      tags:
        Department: MLOps
      email_notifications:
        on_failure:
          - mlops-support@imail.org
```

---

## 9. Choosing Regression vs. Classification

When the user describes their use case, follow this decision tree:

| Signal | Model Type | LightGBM Objective | Metric | Monitoring Problem Type |
|--------|-----------|--------------------|---------|-----------------------|
| Continuous target (price, amount, duration, score) | Regression | `regression` | `rmse`, `mae`, `max_error`, `mean_squared_error` | `PROBLEM_TYPE_REGRESSION` |
| Binary target (yes/no, fraud/legit, 0/1) | Binary Classification | `binary` | `accuracy`, `f1`, `precision`, `recall`, `binary_logloss` | `PROBLEM_TYPE_CLASSIFICATION` |
| Multi-class target (category A/B/C, severity levels) | Multi-class Classification | `multiclass` + `num_class` | `accuracy`, `f1_weighted`, `multi_logloss` | `PROBLEM_TYPE_CLASSIFICATION` |

### Supported Frameworks

- **LightGBM** (default in this template): fast gradient boosting for tabular data
- **scikit-learn**: `RandomForestRegressor`, `RandomForestClassifier`, `GradientBoostingClassifier`, `LogisticRegression`
- **XGBoost**: alternative to LightGBM for gradient boosting
- **Custom PyFunc**: wrap any model in `mlflow.pyfunc` for non-standard use cases

---

## 10. Requirements File

Base dependencies for any ML project:

```
mlflow>=2.12.0
numpy>=1.26.0
pandas>=2.1.0
scikit-learn>=1.4.0
matplotlib>=3.8.0
Jinja2>=3.1.0
pyspark>=3.4.0
pytz>=2024.1
pytest>=8.0.0
pyarrow>=14.0.0
```

Add framework-specific deps as needed:
- LightGBM: `lightgbm>=4.0.0`
- XGBoost: `xgboost>=2.0.0`
- Feature Store: `databricks-feature-engineering>=0.5.0`

---

## 11. Testing

Minimal test at `tests/training/test_notebooks.py`:

```python
import pathlib

def test_notebook_format():
    paths = list(pathlib.Path("./notebooks").glob("**/*.py"))
    for f in paths:
        notebook_str = open(str(f)).read()
        assert notebook_str.startswith("# Databricks notebook source")
```

Extend with:
- Unit tests for `validation.py` custom metrics
- Unit tests for `deploy.py` logic
- Integration tests for `predict.py` with mock data

---

## 12. Conventions Checklist

When creating or modifying an ML project, verify:

- [ ] `databricks.yml` has variables for `catalog_name`, `experiment_name`, `model_name`, `id_group_name`
- [ ] Three targets defined: `dev` (default), `test`, `prod`
- [ ] Registered model uses three-level name: `${var.catalog_name}.ds_output.${var.model_name}-model`
- [ ] Every notebook starts with: `%cd`, `%pip install -r`, `restartPython()`
- [ ] Every notebook uses `dbutils.widgets` for parameters (never hardcoded)
- [ ] Training notebook ends with `dbutils.jobs.taskValues.set()` and `dbutils.notebook.exit()`
- [ ] `git_source_info` parameter included in every job task
- [ ] Email notifications on failure: `mlops-support@imail.org`
- [ ] All jobs tagged with `Department: MLOps` and `model_name: ${bundle.name}`
- [ ] Validation thresholds defined in `validation/validation.py`
- [ ] Monitor config defined in `monitoring/notebooks/config.py`
- [ ] `champion` / `challenger` alias pattern used for model promotion
- [ ] Feature Store tables referenced via `FeatureLookup` (when applicable)
- [ ] Bundle validated with `databricks bundle validate --strict --target <target>`
