"""Silver (de todas as coleções da turma) -> Gold: esquema estrela no DuckDB.

Regra de conversão (ADR-003): o preço do dia D usa a PTAX de fechamento do dia D ou, se
não houver, a do dia útil anterior mais próximo. Nunca uma cotação posterior. Implementada
com ASOF JOIN.
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from pokelake.config import Settings
from pokelake.db import connect, read_parquet_sql
from pokelake.keys import GOLD_TABLES, gold_key
from pokelake.storage import BaseLake

log = logging.getLogger("pokelake.gold")


def _staging(con: duckdb.DuckDBPyConnection, lake: BaseLake, s: Settings) -> None:
    """Views de staging sobre a silver de todos os alunos, com tipos forçados ao contrato."""
    rp = lambda pat: read_parquet_sql(lake.uri(pat))  # noqa: E731

    con.execute(
        f"""CREATE OR REPLACE TABLE stg_preco AS
        SELECT CAST(data AS DATE) AS data, CAST(product_id AS INTEGER) AS product_id,
               CAST(group_id AS INTEGER) AS group_id, CAST(acabamento AS VARCHAR) AS acabamento,
               TRY_CAST(market_price AS DOUBLE) AS market_price, TRY_CAST(low_price AS DOUBLE) AS low_price,
               TRY_CAST(mid_price AS DOUBLE) AS mid_price, TRY_CAST(high_price AS DOUBLE) AS high_price,
               CAST(fonte AS VARCHAR) AS fonte
        FROM {rp('silver/preco_diario/*/*/*.parquet')}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY data, product_id, group_id, acabamento ORDER BY chave_raw DESC) = 1"""
    )
    con.execute(
        f"""CREATE OR REPLACE TABLE stg_produto AS
        SELECT CAST(product_id AS INTEGER) AS product_id, CAST(group_id AS INTEGER) AS group_id,
               CAST(nome AS VARCHAR) AS nome, CAST(tipo_produto AS VARCHAR) AS tipo_produto,
               CAST(raridade AS VARCHAR) AS raridade, CAST(numero AS VARCHAR) AS numero,
               CAST(image_url AS VARCHAR) AS image_url, CAST(url AS VARCHAR) AS url
        FROM {rp('silver/produto/*/*.parquet')}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY group_id) = 1"""
    )
    con.execute(
        f"""CREATE OR REPLACE TABLE stg_colecao AS
        SELECT CAST(group_id AS INTEGER) AS group_id, CAST(nome AS VARCHAR) AS nome,
               CAST(sigla AS VARCHAR) AS sigla, CAST(data_lancamento AS DATE) AS data_lancamento,
               CAST(responsavel AS VARCHAR) AS responsavel
        FROM {rp('silver/colecao/*/*.parquet')}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY group_id ORDER BY responsavel) = 1"""
    )
    # PTAX e CDI são iguais para todos: união das cópias de todos os alunos, deduplicada por dia.
    con.execute(
        f"""CREATE OR REPLACE TABLE stg_cambio AS
        SELECT CAST(data AS DATE) AS data, CAST(cotacao_compra AS DOUBLE) AS cotacao_compra,
               CAST(cotacao_venda AS DOUBLE) AS cotacao_venda, CAST(data_hora_cotacao AS TIMESTAMP) AS data_hora_cotacao
        FROM {rp('silver/cambio_diario/*/*.parquet')}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY data ORDER BY data_hora_cotacao DESC) = 1"""
    )
    con.execute(
        f"""CREATE OR REPLACE TABLE stg_cdi AS
        SELECT CAST(data AS DATE) AS data, CAST(taxa_dia AS DOUBLE) AS taxa_dia
        FROM {rp('silver/cdi_diario/*/*.parquet')}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY data ORDER BY chave_raw DESC) = 1"""
    )


def build_gold_tables(con: duckdb.DuckDBPyConnection, lake: BaseLake, s: Settings) -> None:
    _staging(con, lake, s)

    con.execute(
        """CREATE OR REPLACE TABLE dim_colecao AS
        SELECT group_id, nome, sigla,
               CASE WHEN nome LIKE 'ME%' THEN 'Mega Evolution' ELSE 'Scarlet & Violet' END AS serie,
               data_lancamento, responsavel
        FROM stg_colecao"""
    )
    con.execute(
        """CREATE OR REPLACE TABLE dim_produto AS
        SELECT product_id, group_id, nome, tipo_produto,
               CASE
                 WHEN tipo_produto = 'carta' THEN NULL
                 WHEN lower(nome) LIKE '%booster box case%' THEN 'Booster Box Case'
                 WHEN lower(nome) LIKE '%booster box%' THEN 'Booster Box'
                 WHEN lower(nome) LIKE '%elite trainer box%' THEN 'Elite Trainer Box'
                 WHEN lower(nome) LIKE '%booster bundle%' THEN 'Booster Bundle'
                 WHEN lower(nome) LIKE '%blister%' THEN 'Blister'
                 ELSE 'Outros selados'
               END AS categoria_selado,
               raridade, numero, image_url, url,
               (coalesce(raridade, '') = 'Code Card' OR lower(nome) LIKE '%code card%') AS is_code_card
        FROM stg_produto"""
    )
    con.execute(
        """CREATE OR REPLACE TABLE dim_acabamento AS
        SELECT CAST(dense_rank() OVER (ORDER BY acabamento) AS INTEGER) AS acabamento_id, acabamento
        FROM (SELECT DISTINCT acabamento FROM stg_preco)"""
    )
    con.execute(
        """CREATE OR REPLACE TABLE dim_data AS
        SELECT CAST(d AS DATE) AS data,
               CAST(year(CAST(d AS DATE)) AS INTEGER) AS ano,
               CAST(month(CAST(d AS DATE)) AS INTEGER) AS mes,
               CAST(weekofyear(CAST(d AS DATE)) AS INTEGER) AS semana,
               dayname(CAST(d AS DATE)) AS dia_semana,
               isodow(CAST(d AS DATE)) >= 6 AS fim_de_semana
        FROM (SELECT unnest(generate_series(min(data), max(data), INTERVAL 1 DAY)) AS d FROM stg_preco)"""
    )
    # fato_cambio_diario: um dia de calendário, PTAX aplicada (última conhecida) e CDI do dia.
    con.execute(
        """CREATE OR REPLACE TABLE fato_cambio_diario AS
        WITH cal AS (SELECT data FROM dim_data),
        com_ptax AS (
            SELECT cal.data, p.data AS data_ptax, p.cotacao_compra, p.cotacao_venda
            FROM cal ASOF LEFT JOIN stg_cambio p ON cal.data >= p.data
        )
        SELECT c.data, c.data_ptax, c.cotacao_compra, c.cotacao_venda,
               COALESCE(d.taxa_dia, 0.0) AS cdi_taxa_dia,   -- 0 em dia sem taxa (fim de semana/feriado)
               (d.taxa_dia IS NOT NULL) AS tem_cdi
        FROM com_ptax c LEFT JOIN stg_cdi d ON d.data = c.data
        ORDER BY c.data"""
    )
    con.execute(
        """CREATE OR REPLACE TABLE fato_preco_diario AS
        SELECT p.data, p.product_id, p.group_id, p.acabamento, a.acabamento_id,
               p.market_price, p.low_price, p.mid_price, p.high_price,
               c.cotacao_venda, c.cotacao_compra, c.data AS data_ptax,
               p.market_price * c.cotacao_venda AS market_price_brl,
               p.low_price * c.cotacao_venda AS low_price_brl,
               p.mid_price * c.cotacao_venda AS mid_price_brl,
               p.high_price * c.cotacao_venda AS high_price_brl,
               p.fonte
        FROM stg_preco p
        ASOF LEFT JOIN stg_cambio c ON p.data >= c.data
        LEFT JOIN dim_acabamento a ON a.acabamento = p.acabamento
        ORDER BY p.group_id, p.product_id, p.acabamento, p.data"""
    )


def build_gold(lake: BaseLake, s: Settings, con: duckdb.DuckDBPyConnection | None = None) -> dict:
    """Constrói o modelo dimensional e exporta cada tabela para gold/group_id=X/<tabela>.parquet."""
    con = con or connect(lake, s)
    build_gold_tables(con, lake, s)
    contagens = {}
    for t in GOLD_TABLES:
        uri = lake.uri(gold_key(s.group_id, t))
        if lake.kind == "local":
            Path(uri).parent.mkdir(parents=True, exist_ok=True)
        con.execute(f"COPY {t} TO '{uri}' (FORMAT PARQUET)")
        contagens[t] = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    log.info("gold group_id=%s: %s", s.group_id, contagens)
    return contagens
