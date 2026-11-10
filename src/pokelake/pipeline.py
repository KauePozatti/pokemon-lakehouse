"""Etapa de carteira e orquestração de ponta a ponta."""
from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from pokelake.analytics import load_prices
from pokelake.collect import collect
from pokelake.config import Settings
from pokelake.db import connect
from pokelake.gold import build_gold
from pokelake.keys import carteira_turma_key, gold_key
from pokelake.models import CARTEIRA_SCHEMA
from pokelake.portfolio import PortfolioConfig, metricas, simulate
from pokelake.silver import build_silver
from pokelake.storage import BaseLake

log = logging.getLogger("pokelake.pipeline")


def _put_parquet(lake: BaseLake, key: str, tbl: pa.Table) -> None:
    buf = io.BytesIO()
    pq.write_table(tbl, buf, compression="zstd")
    lake.put(key, buf.getvalue())


def build_portfolio(lake: BaseLake, s: Settings, con=None) -> dict:
    """Calcula as cinco carteiras (com e sem taxa de venda) e grava no lake.

    - gold_turma/carteira/group_id=X/carteira.parquet  -> contrato comum (taxa de venda padrão)
    - gold/group_id=X/carteira_sensibilidade.parquet   -> taxa padrão e taxa 0 (ponto de sensibilidade do ATAM)
    - gold/group_id=X/carteira_composicao.parquet      -> o que foi comprado, em unidades inteiras
    """
    con = con or connect(lake, s)
    prices = load_prices(_gold_views(con, lake, s))
    cambio = con.execute("SELECT * FROM fato_cambio_diario").df()

    base = PortfolioConfig(taxa_venda=s.taxa_venda)
    curvas, comp = simulate(prices, cambio, s.group_id, base)
    curvas0, _ = simulate(prices, cambio, s.group_id, PortfolioConfig(taxa_venda=0.0))

    contrato = pa.Table.from_pandas(curvas[[f.name for f in CARTEIRA_SCHEMA]], schema=CARTEIRA_SCHEMA, preserve_index=False)
    _put_parquet(lake, carteira_turma_key(s.group_id), contrato)
    _put_parquet(lake, gold_key(s.group_id, "carteira_sensibilidade"), pa.Table.from_pandas(
        pd.concat([curvas, curvas0], ignore_index=True), preserve_index=False))
    _put_parquet(lake, gold_key(s.group_id, "carteira_composicao"), pa.Table.from_pandas(comp, preserve_index=False))
    m = metricas(curvas)
    log.info("carteiras group_id=%s:\n%s", s.group_id, m.to_string(index=False))
    return {"metricas": m, "dias": int(curvas["data"].nunique())}


def _gold_views(con, lake: BaseLake, s: Settings):
    """Registra views fato_*/dim_* sobre o gold exportado (o que o dashboard também lê)."""
    from pokelake.db import read_parquet_sql
    from pokelake.keys import GOLD_TABLES

    for t in GOLD_TABLES:
        con.execute(f"CREATE OR REPLACE TEMP VIEW {t} AS SELECT * FROM {read_parquet_sql(lake.uri(gold_key(s.group_id, t)))}")
    return con


def rebuild(lake: BaseLake, s: Settings, group_ids: list[int] | None = None) -> dict:
    """Um comando para reconstruir tudo que é derivado: silver -> gold -> carteira."""
    out = {"silver": [build_silver(lake, s, gid, full=True) for gid in (group_ids or [s.group_id])]}
    con = connect(lake, s)
    out["gold"] = build_gold(lake, s, con)
    out["carteira"] = build_portfolio(lake, s, con)
    return out


def run_daily(lake: BaseLake, s: Settings, allow_stale: bool = False) -> dict:
    """Coleta do dia e reconstrução das camadas derivadas."""
    rel = collect(lake, s, allow_stale=allow_stale)
    out = rebuild(lake, s)
    out["coleta"] = rel
    return out
