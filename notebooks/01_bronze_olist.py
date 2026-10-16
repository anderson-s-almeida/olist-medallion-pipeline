# Databricks notebook source
# MAGIC %md
# MAGIC # 01 - Bronze | Olist
# MAGIC Lê os CSVs brutos do volume e grava cada arquivo como tabela Delta na camada bronze,
# MAGIC sem transformações, apenas com colunas de auditoria.

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "workspace"
RAW_PATH = f"/Volumes/{CATALOG}/olist/raw"
BRONZE_SCHEMA = f"{CATALOG}.olist_bronze"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {BRONZE_SCHEMA}")

# COMMAND ----------

# arquivo de origem -> nome da tabela bronze
ARQUIVOS = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "category_translation",
}

# COMMAND ----------

def ingerir_bronze(arquivo: str, tabela: str) -> int:
    """Lê um CSV bruto e grava como Delta (overwrite) com colunas de auditoria."""
    df = (
        spark.read
        .option("header", True)
        .option("multiLine", True)      # reviews possuem quebras de linha no texto
        .option("escape", '"')
        .csv(f"{RAW_PATH}/{arquivo}")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.lit(arquivo))
    )

    (
        df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", True)
        .saveAsTable(f"{BRONZE_SCHEMA}.{tabela}")
    )
    return df.count()

# COMMAND ----------

resumo = []
for arquivo, tabela in ARQUIVOS.items():
    linhas = ingerir_bronze(arquivo, tabela)
    resumo.append((tabela, linhas))
    print(f"[bronze] {tabela:<22} {linhas:>10,} linhas")

display(spark.createDataFrame(resumo, ["tabela", "linhas"]))
