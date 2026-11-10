"""Convenção de chaves do data lake da turma (ver página do projeto)."""
from __future__ import annotations

from datetime import date

GOLD_TABLES = [
    "dim_colecao",
    "dim_produto",
    "dim_data",
    "dim_acabamento",
    "fato_preco_diario",
    "fato_cambio_diario",
]


def raw_key(source: str, group_id: int, d: date, filename: str) -> str:
    return f"raw/{source}/group_id={group_id}/data={d.isoformat()}/{filename}"


def raw_prefix(source: str, group_id: int) -> str:
    return f"raw/{source}/group_id={group_id}/"


def silver_key(table: str, group_id: int, filename: str, d: date | None = None) -> str:
    part = f"data={d.isoformat()}/" if d else ""
    return f"silver/{table}/group_id={group_id}/{part}{filename}"


def quarentena_key(table: str, group_id: int, d: date, ts: str) -> str:
    return f"quarentena/{table}/group_id={group_id}/data={d.isoformat()}/{ts}.jsonl"


def gold_key(group_id: int, table: str) -> str:
    return f"gold/group_id={group_id}/{table}.parquet"


def carteira_turma_key(group_id: int) -> str:
    return f"gold_turma/carteira/group_id={group_id}/carteira.parquet"
