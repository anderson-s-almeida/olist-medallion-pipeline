"""
DAG: olist_medallion_pipeline

Orquestra o pipeline medalhão da Olist no Databricks:
    bronze  ->  silver  ->  gold

Pré-requisitos no Airflow:
    - Conexão `databricks_default` (host do workspace + token)
    - Variáveis: olist_job_bronze, olist_job_silver, olist_job_gold (IDs dos Jobs)
"""

from datetime import datetime, timedelta

from airflow.models import Variable
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator
from airflow.sdk import DAG

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="olist_medallion_pipeline",
    description="Olist: bronze -> silver -> gold no Databricks",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule="0 6 * * *",          # todos os dias às 06:00
    catchup=False,
    max_active_runs=1,
    tags=["olist", "databricks", "medallion"],
) as dag:

    bronze = DatabricksRunNowOperator(
        task_id="bronze_ingestao",
        databricks_conn_id="databricks_default",
        job_id=Variable.get("olist_job_bronze"),
    )

    silver = DatabricksRunNowOperator(
        task_id="silver_tratamento",
        databricks_conn_id="databricks_default",
        job_id=Variable.get("olist_job_silver"),
    )

    gold = DatabricksRunNowOperator(
        task_id="gold_modelagem",
        databricks_conn_id="databricks_default",
        job_id=Variable.get("olist_job_gold"),
    )

    bronze >> silver >> gold
