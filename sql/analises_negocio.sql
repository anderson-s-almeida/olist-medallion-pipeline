-- =====================================================================
-- Olist | Análises de negócio sobre a camada gold
-- Executar no SQL Editor do Databricks (catálogo: workspace)
-- =====================================================================

-- 1) Evolução mensal: receita, pedidos e ticket médio + crescimento MoM
WITH mensal AS (
    SELECT d.ano_mes,
           COUNT(DISTINCT f.order_id) AS pedidos,
           SUM(f.valor_total)         AS receita
    FROM workspace.olist_gold.fato_vendas f
    JOIN workspace.olist_gold.dim_data d ON d.sk_data = f.sk_data_compra
    WHERE f.status = 'delivered'
    GROUP BY d.ano_mes
)
SELECT ano_mes,
       pedidos,
       ROUND(receita, 2)                                   AS receita,
       ROUND(receita / pedidos, 2)                         AS ticket_medio,
       ROUND(100 * (receita / LAG(receita) OVER (ORDER BY ano_mes) - 1), 1) AS cresc_mom_pct
FROM mensal
ORDER BY ano_mes;


-- 2) Top 10 categorias por receita e participação no total
SELECT p.categoria,
       ROUND(SUM(f.valor_total), 2) AS receita,
       ROUND(100 * SUM(f.valor_total) / SUM(SUM(f.valor_total)) OVER (), 2) AS participacao_pct
FROM workspace.olist_gold.fato_vendas f
JOIN workspace.olist_gold.dim_produto p USING (product_id)
WHERE f.status = 'delivered'
GROUP BY p.categoria
ORDER BY receita DESC
LIMIT 10;


-- 3) Percentual de pedidos entregues com atraso por UF
SELECT c.uf,
       COUNT(DISTINCT f.order_id) AS pedidos,
       ROUND(100 * AVG(CAST(f.entregue_com_atraso AS INT)), 1) AS pct_atraso,
       ROUND(AVG(f.dias_entrega), 1)                          AS media_dias_entrega
FROM workspace.olist_gold.fato_vendas f
JOIN workspace.olist_gold.dim_cliente c USING (customer_id)
WHERE f.status = 'delivered'
GROUP BY c.uf
ORDER BY pct_atraso DESC;


-- 4) Atraso x nota de avaliação
SELECT CASE WHEN entregue_com_atraso THEN 'Com atraso' ELSE 'No prazo' END AS entrega,
       COUNT(DISTINCT order_id)        AS pedidos,
       ROUND(AVG(nota_avaliacao), 2)   AS nota_media
FROM workspace.olist_gold.fato_vendas
WHERE status = 'delivered' AND entregue_com_atraso IS NOT NULL
GROUP BY 1;


-- 5) Ranking de vendedores por receita dentro de cada UF (top 3)
WITH vendas_vendedor AS (
    SELECT v.uf, v.seller_id,
           SUM(f.valor_total)         AS receita,
           AVG(f.nota_avaliacao)      AS nota_media
    FROM workspace.olist_gold.fato_vendas f
    JOIN workspace.olist_gold.dim_vendedor v USING (seller_id)
    WHERE f.status = 'delivered'
    GROUP BY v.uf, v.seller_id
)
SELECT *
FROM (
    SELECT *, DENSE_RANK() OVER (PARTITION BY uf ORDER BY receita DESC) AS posicao
    FROM vendas_vendedor
)
WHERE posicao <= 3
ORDER BY uf, posicao;


-- 6) Recompra: clientes únicos com mais de um pedido
SELECT COUNT(*)                                             AS clientes,
       SUM(CASE WHEN pedidos > 1 THEN 1 ELSE 0 END)         AS clientes_recorrentes,
       ROUND(100 * AVG(CASE WHEN pedidos > 1 THEN 1 ELSE 0 END), 2) AS taxa_recompra_pct
FROM (
    SELECT c.customer_unique_id, COUNT(DISTINCT f.order_id) AS pedidos
    FROM workspace.olist_gold.fato_vendas f
    JOIN workspace.olist_gold.dim_cliente c USING (customer_id)
    GROUP BY c.customer_unique_id
);
