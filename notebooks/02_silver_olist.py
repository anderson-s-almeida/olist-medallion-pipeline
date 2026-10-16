# Databricks notebook source
# MAGIC %md
# MAGIC # 02 - Silver | Olist
# MAGIC Limpeza, tipagem, deduplicação e padronização das tabelas bronze.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

CATALOG = "workspace"
BRONZE = f"{CATALOG}.olist_bronze"
SILVER = f"{CATALOG}.olist_silver"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SILVER}")

def ler(tabela: str):
    return spark.table(f"{BRONZE}.{tabela}").drop("_ingested_at", "_source_file")

def gravar(df, tabela: str):
    (
        df.withColumn("_processed_at", F.current_timestamp())
        .write.format("delta").mode("overwrite").option("overwriteSchema", True)
        .saveAsTable(f"{SILVER}.{tabela}")
    )
    print(f"[silver] {tabela:<16} {df.count():>10,} linhas")

def texto(col):
    """Remove espaços extras e padroniza em minúsculas."""
    return F.lower(F.trim(F.col(col)))

# COMMAND ----------

# MAGIC %md ## Clientes

# COMMAND ----------

clientes = (
    ler("customers")
    .select(
        "customer_id",
        "customer_unique_id",
        F.lpad("customer_zip_code_prefix", 5, "0").alias("cep_prefixo"),
        F.initcap(F.trim("customer_city")).alias("cidade"),
        F.upper(F.trim("customer_state")).alias("uf"),
    )
    .dropDuplicates(["customer_id"])
)
gravar(clientes, "clientes")

# COMMAND ----------

# MAGIC %md ## Pedidos

# COMMAND ----------

pedidos = (
    ler("orders")
    .select(
        "order_id",
        "customer_id",
        texto("order_status").alias("status"),
        F.to_timestamp("order_purchase_timestamp").alias("dt_compra"),
        F.to_timestamp("order_approved_at").alias("dt_aprovacao"),
        F.to_timestamp("order_delivered_carrier_date").alias("dt_envio"),
        F.to_timestamp("order_delivered_customer_date").alias("dt_entrega"),
        F.to_timestamp("order_estimated_delivery_date").alias("dt_entrega_estimada"),
    )
    .dropDuplicates(["order_id"])
    .withColumn(
        "dias_entrega",
        F.datediff(F.col("dt_entrega"), F.col("dt_compra")),
    )
    .withColumn(
        "entregue_com_atraso",
        F.when(F.col("dt_entrega").isNull(), None)
         .otherwise(F.col("dt_entrega") > F.col("dt_entrega_estimada")),
    )
)
gravar(pedidos, "pedidos")

# COMMAND ----------

# MAGIC %md ## Itens do pedido

# COMMAND ----------

itens = (
    ler("order_items")
    .select(
        "order_id",
        F.col("order_item_id").cast("int").alias("item_seq"),
        "product_id",
        "seller_id",
        F.to_timestamp("shipping_limit_date").alias("dt_limite_envio"),
        F.col("price").cast("decimal(12,2)").alias("preco"),
        F.col("freight_value").cast("decimal(12,2)").alias("frete"),
    )
    .dropDuplicates(["order_id", "item_seq"])
)
gravar(itens, "itens_pedido")

# COMMAND ----------

# MAGIC %md ## Pagamentos

# COMMAND ----------

pagamentos = (
    ler("order_payments")
    .select(
        "order_id",
        F.col("payment_sequential").cast("int").alias("pagamento_seq"),
        texto("payment_type").alias("tipo_pagamento"),
        F.col("payment_installments").cast("int").alias("parcelas"),
        F.col("payment_value").cast("decimal(12,2)").alias("valor"),
    )
    .dropDuplicates(["order_id", "pagamento_seq"])
)
gravar(pagamentos, "pagamentos")

# COMMAND ----------

# MAGIC %md ## Avaliações
# MAGIC Há reviews duplicados por pedido: mantém o mais recente.

# COMMAND ----------

janela_review = Window.partitionBy("order_id").orderBy(F.col("dt_resposta").desc())

avaliacoes = (
    ler("order_reviews")
    .select(
        "review_id",
        "order_id",
        F.col("review_score").cast("int").alias("nota"),
        F.to_timestamp("review_creation_date").alias("dt_criacao"),
        F.to_timestamp("review_answer_timestamp").alias("dt_resposta"),
    )
    .filter(F.col("nota").between(1, 5))
    .withColumn("rn", F.row_number().over(janela_review))
    .filter("rn = 1")
    .drop("rn")
)
gravar(avaliacoes, "avaliacoes")

# COMMAND ----------

# MAGIC %md ## Produtos (com tradução da categoria)

# COMMAND ----------

traducao = ler("category_translation").select(
    texto("product_category_name").alias("categoria"),
    texto("product_category_name_english").alias("categoria_en"),
)

produtos = (
    ler("products")
    .select(
        "product_id",
        F.coalesce(texto("product_category_name"), F.lit("sem_categoria")).alias("categoria"),
        F.col("product_weight_g").cast("int").alias("peso_g"),
        F.col("product_length_cm").cast("int").alias("comprimento_cm"),
        F.col("product_height_cm").cast("int").alias("altura_cm"),
        F.col("product_width_cm").cast("int").alias("largura_cm"),
        F.col("product_photos_qty").cast("int").alias("qtd_fotos"),
    )
    .dropDuplicates(["product_id"])
    .join(traducao, "categoria", "left")
)
gravar(produtos, "produtos")

# COMMAND ----------

# MAGIC %md ## Vendedores

# COMMAND ----------

vendedores = (
    ler("sellers")
    .select(
        "seller_id",
        F.lpad("seller_zip_code_prefix", 5, "0").alias("cep_prefixo"),
        F.initcap(F.trim("seller_city")).alias("cidade"),
        F.upper(F.trim("seller_state")).alias("uf"),
    )
    .dropDuplicates(["seller_id"])
)
gravar(vendedores, "vendedores")
