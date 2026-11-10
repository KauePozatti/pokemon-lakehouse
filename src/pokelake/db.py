"""Conexão DuckDB já configurada para ler/escrever Parquet no lake (extensão httpfs)."""
from __future__ import annotations

from urllib.parse import urlparse

import duckdb

from pokelake.config import Settings
from pokelake.storage import BaseLake


def _esc(v: str) -> str:
    return v.replace("'", "''")


def connect(lake: BaseLake, s: Settings) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    if lake.kind == "s3":
        con.execute("INSTALL httpfs; LOAD httpfs;")
        u = urlparse(s.endpoint_url)
        host = u.netloc or u.path
        use_ssl = "true" if u.scheme != "http" else "false"
        con.execute(
            f"""CREATE OR REPLACE SECRET lake (
                TYPE S3, KEY_ID '{_esc(s.access_key)}', SECRET '{_esc(s.secret_key)}',
                ENDPOINT '{_esc(host)}', URL_STYLE 'path', USE_SSL {use_ssl}, REGION '{_esc(s.region)}')"""
        )
    return con


def read_parquet_sql(uri: str) -> str:
    """Fragmento SQL para ler Parquet sem inferir partições Hive do caminho.

    `group_id=` e `data=` já existem como colunas nos arquivos; ler com hive_partitioning
    duplicaria as colunas. `union_by_name` tolera colunas extras dos colegas.
    """
    return f"read_parquet('{_esc(uri)}', union_by_name=true, hive_partitioning=false)"
