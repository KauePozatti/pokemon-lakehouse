"""Bruto -> Silver: parsing, validação Pydantic, quarentena e Parquet tipado.

Tudo aqui é derivado do bruto e pode ser reconstruído com `python -m pokelake rebuild`.
"""
from __future__ import annotations

import io
import json
import logging
import re
from datetime import date, datetime

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ValidationError

from pokelake.config import COLECOES, GROUP_TO_SIGLA, Settings
from pokelake.keys import quarentena_key, raw_prefix, silver_key
from pokelake.models import (
    SCHEMAS,
    CambioDiarioSilver,
    CdiDiarioSilver,
    ColecaoSilver,
    PrecoDiarioSilver,
    ProdutoSilver,
)
from pokelake.storage import BaseLake

log = logging.getLogger("pokelake.silver")
_DATA_RE = re.compile(r"data=(\d{4}-\d{2}-\d{2})/")


# --------------------------------------------------------------------------- parsing
def _ext(prod: dict, nome: str):
    for e in prod.get("extendedData") or []:
        if e.get("name") == nome:
            return e.get("value")
    return None


def parse_products(raw: bytes, group_id: int) -> list[dict]:
    rows = []
    for p in json.loads(raw).get("results", []):
        numero = _ext(p, "Number")
        rows.append(
            {
                "product_id": p.get("productId"),
                "group_id": group_id,
                "nome": p.get("name"),
                # Carta tem número de coleção; produto sem número é selado (box, bundle, ETB...).
                "tipo_produto": "carta" if numero else "selado",
                "raridade": _ext(p, "Rarity"),
                "numero": numero,
                "image_url": p.get("imageUrl"),
                "url": p.get("url"),
            }
        )
    return rows


def parse_prices(raw: bytes, d: date, group_id: int, chave_raw: str) -> list[dict]:
    rows = []
    for p in json.loads(raw).get("results", []):
        rows.append(
            {
                "data": d,
                "product_id": p.get("productId"),
                "group_id": group_id,
                "acabamento": p.get("subTypeName"),
                "market_price": p.get("marketPrice"),  # None permanece None
                "low_price": p.get("lowPrice"),
                "mid_price": p.get("midPrice"),
                "high_price": p.get("highPrice"),
                "moeda": "USD",
                "fonte": "tcgplayer/tcgcsv",
                "chave_raw": chave_raw,
            }
        )
    return rows


def parse_ptax(raw: bytes, d: date, chave_raw: str) -> list[dict]:
    """Só o boletim de Fechamento. Dia sem boletim (fim de semana/feriado) devolve []."""
    boletins = [b for b in json.loads(raw).get("value", []) if b.get("tipoBoletim") == "Fechamento"]
    if not boletins:
        return []
    b = max(boletins, key=lambda x: x["dataHoraCotacao"])
    return [
        {
            "data": d,
            "cotacao_compra": b["cotacaoCompra"],
            "cotacao_venda": b["cotacaoVenda"],
            "data_hora_cotacao": datetime.fromisoformat(b["dataHoraCotacao"].replace(" ", "T")),
            "boletim": "Fechamento",
            "chave_raw": chave_raw,
        }
    ]


def parse_cdi(raw: bytes, chave_raw: str) -> list[dict]:
    rows = []
    for r in json.loads(raw):
        rows.append(
            {
                "data": datetime.strptime(r["data"], "%d/%m/%Y").date(),
                "taxa_dia": float(r["valor"]),
                "chave_raw": chave_raw,
            }
        )
    return rows


# --------------------------------------------------------------------------- validação
def validar(model: type[BaseModel], rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Devolve (válidos, rejeitados). Rejeitado = {'motivo': ..., 'registro': ...}."""
    ok, rej = [], []
    for r in rows:
        try:
            ok.append(model(**r).model_dump())
        except (ValidationError, TypeError) as e:
            motivo = "; ".join(f"{'.'.join(map(str, er['loc']))}: {er['msg']}" for er in e.errors()) if isinstance(
                e, ValidationError
            ) else str(e)
            rej.append({"motivo": motivo, "registro": r})
    return ok, rej


def _parquet_bytes(rows: list[dict], tabela: str) -> bytes:
    schema = SCHEMAS[tabela]
    tbl = pa.Table.from_pylist(rows, schema=schema)
    buf = io.BytesIO()
    pq.write_table(tbl, buf, compression="zstd")
    return buf.getvalue()


def _json_default(o):
    return o.isoformat() if isinstance(o, (date, datetime)) else str(o)


# --------------------------------------------------------------------------- orquestração
def _dias_raw(lake: BaseLake, fonte: str, gid: int, arquivo: str) -> list[tuple[date, str]]:
    out = []
    for k in lake.list_keys(raw_prefix(fonte, gid)):
        m = _DATA_RE.search(k)
        if m and k.endswith("/" + arquivo):
            out.append((date.fromisoformat(m.group(1)), k))
    return sorted(out)


def build_silver(
    lake: BaseLake,
    s: Settings,
    group_id: int | None = None,
    responsavel: str | None = None,
    full: bool = True,
    agora: datetime | None = None,
) -> dict:
    """Reconstrói a silver de UMA coleção a partir do bruto. Retorna contagens para o log."""
    gid = group_id or s.group_id
    sigla = GROUP_TO_SIGLA.get(gid)
    if sigla is None:
        raise ValueError(f"group_id {gid} fora do catálogo de coleções")
    resp = responsavel if responsavel is not None else s.responsavel
    agora = agora or datetime.now()
    stats = {"group_id": gid, "dias_precos": 0, "preco_linhas": 0, "quarentena": 0}
    rejeitados: dict[str, list[dict]] = {}

    def _quarentena(tabela: str, rej: list[dict]):
        if rej:
            rejeitados.setdefault(tabela, []).extend(rej)

    # colecao
    c = COLECOES[sigla]
    ok, rej = validar(
        ColecaoSilver,
        [{"group_id": gid, "nome": c["nome"], "sigla": sigla, "data_lancamento": c["data_lancamento"], "responsavel": resp}],
    )
    _quarentena("colecao", rej)
    lake.put(silver_key("colecao", gid, "colecao.parquet"), _parquet_bytes(ok, "colecao"))

    # produto: último snapshot de cada product_id vence
    produtos: dict[int, dict] = {}
    for _, k in _dias_raw(lake, "tcgplayer", gid, "products.json"):
        for r in parse_products(lake.get(k), gid):
            if r["product_id"] is not None:
                produtos[r["product_id"]] = r
    ok, rej = validar(ProdutoSilver, list(produtos.values()))
    _quarentena("produto", rej)
    lake.put(silver_key("produto", gid, "produto.parquet"), _parquet_bytes(ok, "produto"))
    stats["produtos"] = len(ok)

    # preco_diario: um arquivo por dia
    for d, k in _dias_raw(lake, "tcgplayer", gid, "prices.json"):
        dest = silver_key("preco_diario", gid, "preco.parquet", d)
        if not full and lake.exists(dest):
            continue
        ok, rej = validar(PrecoDiarioSilver, parse_prices(lake.get(k), d, gid, k))
        # (produto, acabamento) é a chave do grão; duplicata é mantida só uma vez
        vistos, unicos = set(), []
        for r in ok:
            kk = (r["product_id"], r["acabamento"])
            if kk not in vistos:
                vistos.add(kk)
                unicos.append(r)
        _quarentena("preco_diario", rej)
        lake.put(dest, _parquet_bytes(unicos, "preco_diario"))
        stats["dias_precos"] += 1
        stats["preco_linhas"] += len(unicos)

    # cambio_diario (PTAX de fechamento)
    cambio: dict[date, dict] = {}
    for d, k in _dias_raw(lake, "bcb_ptax", gid, "cotacao.json"):
        ok, rej = validar(CambioDiarioSilver, parse_ptax(lake.get(k), d, k))
        _quarentena("cambio_diario", rej)
        for r in ok:
            cambio[r["data"]] = r
    lake.put(
        silver_key("cambio_diario", gid, "cambio.parquet"),
        _parquet_bytes([cambio[d] for d in sorted(cambio)], "cambio_diario"),
    )
    stats["cambio_dias"] = len(cambio)

    # cdi_diario (a janela mais recente vence)
    cdi: dict[date, dict] = {}
    for _, k in _dias_raw(lake, "bcb_cdi", gid, "cdi.json"):
        ok, rej = validar(CdiDiarioSilver, parse_cdi(lake.get(k), k))
        _quarentena("cdi_diario", rej)
        for r in ok:
            cdi[r["data"]] = r
    lake.put(
        silver_key("cdi_diario", gid, "cdi.parquet"),
        _parquet_bytes([cdi[d] for d in sorted(cdi)], "cdi_diario"),
    )
    stats["cdi_dias"] = len(cdi)

    # quarentena/: registro rejeitado + motivo
    ts = agora.strftime("%Y%m%dT%H%M%S")
    for tabela, rej in rejeitados.items():
        corpo = "\n".join(json.dumps(r, default=_json_default, ensure_ascii=False) for r in rej)
        lake.put(quarentena_key(tabela, gid, agora.date(), ts), corpo.encode(), "application/x-ndjson")
        stats["quarentena"] += len(rej)
        log.warning("quarentena %s: %d registro(s) rejeitado(s)", tabela, len(rej))

    log.info("silver group_id=%s: %s", gid, stats)
    return stats
