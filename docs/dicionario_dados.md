# 📖 Dicionário de dados – camada gold

## fato_vendas
Grão: **um item de um pedido**.

| Coluna | Tipo | Descrição |
|---|---|---|
| order_id | string | Identificador do pedido |
| item_seq | int | Sequência do item dentro do pedido |
| customer_id | string | FK → dim_cliente |
| product_id | string | FK → dim_produto |
| seller_id | string | FK → dim_vendedor |
| sk_data_compra | int | FK → dim_data (yyyyMMdd) |
| status | string | Status do pedido (delivered, shipped, canceled…) |
| preco | decimal(12,2) | Preço do item |
| frete | decimal(12,2) | Valor do frete do item |
| valor_total | decimal | preco + frete |
| dias_entrega | int | Dias entre compra e entrega |
| entregue_com_atraso | boolean | Entrega após a data estimada |
| nota_avaliacao | int | Nota do pedido (1 a 5) |

## dim_cliente
| Coluna | Descrição |
|---|---|
| customer_id | Chave do cliente no pedido |
| customer_unique_id | Identificador único da pessoa (permite medir recompra) |
| cidade, uf, cep_prefixo | Localização |

## dim_produto
| Coluna | Descrição |
|---|---|
| product_id | Chave do produto |
| categoria / categoria_en | Categoria em português e inglês |
| peso_g, qtd_fotos | Atributos do produto |

## dim_vendedor
| Coluna | Descrição |
|---|---|
| seller_id | Chave do vendedor |
| cidade, uf, cep_prefixo | Localização |

## dim_data
| Coluna | Descrição |
|---|---|
| sk_data | Chave inteira yyyyMMdd |
| data, ano, trimestre, mes, ano_mes, dia | Atributos de calendário |
| dia_semana_num, fim_de_semana | Dia da semana (1 = domingo) |

## agg_vendas_mensal_uf
Agregado de pedidos entregues por mês e UF: `qtd_pedidos`, `receita`, `ticket_medio`, `pct_atraso`, `nota_media`.
