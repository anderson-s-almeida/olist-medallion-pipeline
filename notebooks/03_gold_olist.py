# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # 03 - Gold | Olist
# MAGIC Modelo estrela para consumo no Power BI:
# MAGIC - `fato_vendas` (grão: item do pedido)
# MAGIC - `dim_cliente`, `dim_produto`, `dim_vendedor`, `dim_data`
# MAGIC - `agg_vendas_mensal_uf` (agregado para análises rápidas)

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "workspace"
SILVER = f"{CATALOG}.olist_silver"
GOLD = f"{CATALOG}.olist_gold"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {GOLD}")

def s(tabela: str):
    return spark.table(f"{SILVER}.{tabela}").drop("_processed_at")

def gravar(df, tabela: str):
    df.write.format("delta").mode("overwrite").option("overwriteSchema", True) \
      .saveAsTable(f"{GOLD}.{tabela}")
    print(f"[gold] {tabela:<22} {df.count():>10,} linhas")

# COMMAND ----------

# MAGIC %md ## Dimensões

# COMMAND ----------

dim_cliente = s("clientes").select(
    "customer_id", "customer_unique_id", "cidade", "uf", "cep_prefixo"
)
gravar(dim_cliente, "dim_cliente")

dim_produto = s("produtos").select(
    "product_id", "categoria", "categoria_en", "peso_g", "qtd_fotos"
)
gravar(dim_produto, "dim_produto")

dim_vendedor = s("vendedores").select("seller_id", "cidade", "uf", "cep_prefixo")
gravar(dim_vendedor, "dim_vendedor")

# COMMAND ----------

# dim_data cobrindo todo o período dos pedidos
limites = s("pedidos").agg(
    F.min(F.to_date("dt_compra")).alias("ini"),
    F.max(F.to_date("dt_entrega_estimada")).alias("fim"),
).first()

dim_data = (
    spark.sql(f"SELECT explode(sequence(DATE'{limites.ini}', DATE'{limites.fim}', INTERVAL 1 DAY)) AS data")
    .select(
        F.date_format("data", "yyyyMMdd").cast("int").alias("sk_data"),
        "data",
        F.year("data").alias("ano"),
        F.quarter("data").alias("trimestre"),
        F.month("data").alias("mes"),
        F.date_format("data", "yyyy-MM").alias("ano_mes"),
        F.dayofmonth("data").alias("dia"),
        F.dayofweek("data").alias("dia_semana_num"),
        (F.dayofweek("data").isin(1, 7)).alias("fim_de_semana"),
    )
)
gravar(dim_data, "dim_data")

# COMMAND ----------

# MAGIC %md ## Fato vendas (grão: item do pedido)

# COMMAND ----------

pedidos = s("pedidos")
avaliacoes = s("avaliacoes").select("order_id", "nota")

fato_vendas = (
    s("itens_pedido")
    .join(pedidos, "order_id", "inner")
    .join(avaliacoes, "order_id", "left")
    .select(
        "order_id",
        "item_seq",
        "customer_id",
        "product_id",
        "seller_id",
        F.date_format("dt_compra", "yyyyMMdd").cast("int").alias("sk_data_compra"),
        "status",
        "preco",
        "frete",
        (F.col("preco") + F.col("frete")).alias("valor_total"),
        "dias_entrega",
        "entregue_com_atraso",
        F.col("nota").alias("nota_avaliacao"),
    )
)
gravar(fato_vendas, "fato_vendas")

# COMMAND ----------

# MAGIC %md ## Agregado mensal por UF

# COMMAND ----------

agg = (
    spark.table(f"{GOLD}.fato_vendas").alias("f")
    .join(spark.table(f"{GOLD}.dim_cliente").alias("c"), "customer_id")
    .join(spark.table(f"{GOLD}.dim_data").alias("d"), F.col("f.sk_data_compra") == F.col("d.sk_data"))
    .filter(F.col("f.status") == "delivered")
    .groupBy("d.ano_mes", "c.uf")
    .agg(
        F.countDistinct("f.order_id").alias("qtd_pedidos"),
        F.sum("f.valor_total").alias("receita"),
        (F.sum("f.valor_total") / F.countDistinct("f.order_id")).alias("ticket_medio"),
        F.avg(F.col("f.entregue_com_atraso").cast("int")).alias("pct_atraso"),
        F.avg("f.nota_avaliacao").alias("nota_media"),
    )
)
gravar(agg, "agg_vendas_mensal_uf")

# COMMAND ----------

# MAGIC %md ## Checagens de qualidade

# COMMAND ----------

checks = {
    "fato sem cliente na dimensão": spark.sql(f"""
        SELECT COUNT(*) FROM {GOLD}.fato_vendas f
        LEFT ANTI JOIN {GOLD}.dim_cliente c USING (customer_id)""").first()[0],
    "fato sem produto na dimensão": spark.sql(f"""
        SELECT COUNT(*) FROM {GOLD}.fato_vendas f
        LEFT ANTI JOIN {GOLD}.dim_produto p USING (product_id)""").first()[0],
    "valor_total negativo": spark.sql(f"""
        SELECT COUNT(*) FROM {GOLD}.fato_vendas WHERE valor_total < 0""").first()[0],
}

for regra, qtd in checks.items():
    print(f"{'OK ' if qtd == 0 else 'ERRO'} | {regra}: {qtd}")

assert all(q == 0 for q in checks.values()), "Falha nas checagens de qualidade da gold"