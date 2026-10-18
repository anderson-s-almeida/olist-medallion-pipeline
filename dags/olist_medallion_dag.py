"""
DAG: olist_medallion_pipeline

Orquestra o pipeline medalhão da Olist no Databricks.
O Job `olist_medallion` tem 3 tarefas encadeadas:
    bronze  ->  silver  ->  gold

Pré-requisitos no Airflow:
    - Conexão `databricks_default` (host do workspace + token)
    - Variável `olist_job_id` (ID do Job no Databricks)
"""

from datetime import datetime, timedelta

from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator
from airflow.sdk import DAG, Variable

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

    rodar_job = DatabricksRunNowOperator(
        task_id="rodar_job_olist_medallion",
        databricks_conn_id="databricks_default",
        job_id=Variable.get("olist_job_id"),
    )
