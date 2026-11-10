from __future__ import annotations

import io
import json
from datetime import date, datetime, time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from pokelake.config import Settings
from pokelake.models import SCHEMAS
from pokelake.storage import LocalLake


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(backend="local", local_root=tmp_path, sigla="DRI", group_id=24269, responsavel="Aluno Teste")


@pytest.fixture
def lake(settings: Settings) -> LocalLake:
    return LocalLake(settings)


def put_parquet(lake, key: str, tabela: str, rows: list[dict]) -> None:
    buf = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMAS[tabela]), buf)
    lake.put(key, buf.getvalue())


def produtos_json() -> bytes:
    return json.dumps(
        {
            "success": True,
            "results": [
                {"productId": 1, "name": "Carta Cara", "imageUrl": "http://img/1", "url": "http://t/1",
                 "extendedData": [{"name": "Rarity", "value": "Special Illustration Rare"}, {"name": "Number", "value": "200/182"}]},
                {"productId": 2, "name": "Carta Comum", "imageUrl": "http://img/2", "url": "http://t/2",
                 "extendedData": [{"name": "Rarity", "value": "Common"}, {"name": "Number", "value": "010/182"}]},
                {"productId": 3, "name": "Destined Rivals Booster Box", "imageUrl": "http://img/3", "url": "http://t/3", "extendedData": []},
            ],
        }
    ).encode()


def precos_json() -> bytes:
    return json.dumps(
        {
            "success": True,
            "results": [
                {"productId": 1, "lowPrice": 90.0, "midPrice": 100.0, "highPrice": 150.0, "marketPrice": 100.0, "subTypeName": "Holofoil"},
                {"productId": 2, "lowPrice": 0.1, "midPrice": 0.2, "highPrice": 0.5, "marketPrice": None, "subTypeName": "Normal"},
                {"productId": 3, "lowPrice": 120.0, "midPrice": 130.0, "highPrice": 160.0, "marketPrice": 130.0, "subTypeName": "Normal"},
                {"productId": 2, "lowPrice": -1.0, "midPrice": 0.2, "highPrice": 0.5, "marketPrice": -3.0, "subTypeName": "Reverse Holofoil"},
            ],
        }
    ).encode()


def ptax_json(compra: float, venda: float, d: date) -> bytes:
    return json.dumps(
        {"value": [
            {"cotacaoCompra": compra - 0.01, "cotacaoVenda": venda - 0.01, "dataHoraCotacao": f"{d} 10:00:00.000", "tipoBoletim": "Abertura"},
            {"cotacaoCompra": compra, "cotacaoVenda": venda, "dataHoraCotacao": f"{d} 13:09:02.713", "tipoBoletim": "Fechamento"},
        ]}
    ).encode()


class FakeFetcher:
    """Substitui o Fetcher: devolve respostas fixas e conta as chamadas."""

    def __init__(self, hoje: date):
        self.hoje = hoje
        self.chamadas: list[str] = []

    def get(self, url: str, params=None) -> bytes:
        self.chamadas.append(url)
        if url.endswith("last-updated.txt"):
            # o TCGCSV publica a atualização do dia por volta de 20h UTC (17h em Brasília)
            return f"{datetime.combine(self.hoje, time(20, 0)).isoformat()}+0000".encode()
        if url.endswith("/products"):
            return produtos_json()
        if url.endswith("/prices"):
            return precos_json()
        if "CotacaoMoedaDia" in url:
            mm, dd, yyyy = params["@dataCotacao"].strip("'").split("-")
            d = date(int(yyyy), int(mm), int(dd))
            return ptax_json(5.0, 5.01, d) if d.weekday() < 5 else json.dumps({"value": []}).encode()
        if "bcdata.sgs.12" in url:
            return json.dumps([{"data": "06/11/2026", "valor": "0.050788"}]).encode()
        raise AssertionError(f"URL inesperada: {url}")
