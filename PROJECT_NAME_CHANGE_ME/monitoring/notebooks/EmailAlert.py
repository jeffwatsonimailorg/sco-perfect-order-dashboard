# Databricks notebook source
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# COMMAND ----------

#CHANGEME: Replace with your own thresholds 
metric_threshold = {
    "accuracy": 0.35,
}

metrics = ", ".join(metric_threshold.keys())
thresholds = ", ".join(map(str, metric_threshold.values()))
values = ", ".join(map(str, metric_threshold.values()))

# COMMAND ----------

# Metrics to be used for threshold violation check
dbutils.widgets.text(
    "metrics_violated", metrics, label="Metric name to be monitored for threshold violation"
) 

dbutils.widgets.text(
    "metric_values", values, label="Current metric value"
) 

# Threshold value to be checked
dbutils.widgets.text(
    "metric_thresholds", thresholds, label="Threshold value for metric violation"
)

# Model name to be used for threshold violation check
dbutils.widgets.text(
    "model_name", "dev_datascience.ds_output.PROJECT_NAME_CHANGE_ME-model", label="Full (Three-Level) Model Name"
)

dbutils.widgets.dropdown("env", "dev_datascience", ["dev_datascience", "staging_datascience", "prod_datascience"], "Environment Name")

# COMMAND ----------

env = dbutils.widgets.get("env")
if not env.endswith("_datascience"):
    env = f"{env}_datascience"

metrics_violated = dbutils.widgets.get("metrics_violated").split(", ")
metric_values = dbutils.widgets.get("metric_values").split(", ")
metric_thresholds = dbutils.widgets.get("metric_thresholds").split(", ")
model_name = dbutils.widgets.get("model_name").split(", ")

# COMMAND ----------

html = f"""\
<html>
  <head>
    <style>
      table {{
        font-family: Arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
      }}
      td, th {{
        border: 1px solid #dddddd;
        text-align: left;
        padding: 8px;
      }}
      tr:nth-child(even) {{
        background-color: #f9f9f9;
      }}
    </style>
  </head>
  <body>
    <p>Hi Team,<br><br>
       The model has violated one or more performance thresholds in the <strong>{env}</strong> environment.<br><br>
       Please find the details below:
    </p>
    <table>
      <tr>
        <th>Metric</th>
        <th>Value</th>
        <th>Threshold</th>
      </tr>
      {''.join(f"<tr><td>{m}</td><td>{v}</td><td>{t}</td></tr>" for m, v, t in zip(metrics_violated, metric_values, metric_thresholds))}
    </table>
    <p>
      The numbers in the above table are for the latest evaluation. If you find this email despite the numbers looking good, it is because the model produced unsatisfactory results in more evaluation windows than allowed. Kindly investigate the issue at your earliest convenience.<br><br>
      Regards,<br>
      Monitoring System
    </p>
  </body>
</html>
"""


# COMMAND ----------

me = "mlops-donotreply@imail.org"
you = "mlops-support@imail.org"

msg = MIMEMultipart('alternative')
msg['Subject'] = f"ALERT: {model_name} Model Threshold Violation"
msg['From'] = me
msg['To'] = you



body = MIMEText(html, 'html')
msg.attach(body)

s = smtplib.SMTP('smtp.co.ihc.com', port=587)
s.sendmail(me, you, msg.as_string())
s.quit()

# COMMAND ----------


