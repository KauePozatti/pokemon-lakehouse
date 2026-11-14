import io
from datetime import date

import pyarrow.parquet as pq

from pokelake.collect import collect
from pokelake.keys import quarentena_key, silver_key
from pokelake.silver import build_silver, parse_prices, parse_products, parse_ptax, validar
from pokelake.models import PrecoDiarioSilver
from tests.conftest import FakeFetcher, precos_json, produtos_json, ptax_json

HOJE = date(2026, 11, 9)


def test_tipo_produto_carta_x_selado():
    rows = {r["product_id"]: r for r in parse_products(produtos_json(), 24269)}
    assert rows[1]["tipo_produto"] == "carta" and rows[1]["raridade"] == "Special Illustration Rare"
    assert rows[3]["tipo_produto"] == "selado" and rows[3]["numero"] is None


def test_nulo_nao_vira_zero():
    ok, rej = validar(PrecoDiarioSilver, parse_prices(precos_json(), HOJE, 24269, "k"))
    nulo = [r for r in ok if r["product_id"] == 2][0]
    assert nulo["market_price"] is None and nulo["low_price"] == 0.1


def test_registro_invalido_vai_para_quarentena(lake, settings):
    collect(lake, settings, fetcher=FakeFetcher(HOJE), hoje=HOJE)
    stats = build_silver(lake, settings)
    assert stats["quarentena"] == 1  # preço negativo
    chaves = lake.list_keys("quarentena/preco_diario/")
    assert len(chaves) == 1
    assert "ge" in lake.get(chaves[0]).decode() or "greater" in lake.get(chaves[0]).decode()


def test_silver_respeita_contrato_de_tipos(lake, settings):
    collect(lake, settings, fetcher=FakeFetcher(HOJE), hoje=HOJE)
    build_silver(lake, settings)
    t = pq.read_table(io.BytesIO(lake.get(silver_key("preco_diario", 24269, "preco.parquet", HOJE))))
    tipos = {f.name: str(f.type) for f in t.schema}
    assert tipos["product_id"] == "int32" and tipos["market_price"] == "double" and tipos["data"] == "date32[day]"
    assert tipos["moeda"] == "string" and tipos["chave_raw"] == "string"
    cambio = pq.read_table(io.BytesIO(lake.get(silver_key("cambio_diario", 24269, "cambio.parquet"))))
    assert set(cambio.column("boletim").to_pylist()) == {"Fechamento"}  # só fechamento


def test_ptax_so_fechamento_e_fim_de_semana_vazio():
    r = parse_ptax(ptax_json(5.00, 5.01, date(2026, 11, 6)), date(2026, 11, 6), "k")
    assert len(r) == 1 and r[0]["cotacao_venda"] == 5.01
    assert parse_ptax(b'{"value": []}', date(2026, 11, 7), "k") == []


def test_silver_e_reconstruivel_do_bruto(lake, settings):
    collect(lake, settings, fetcher=FakeFetcher(HOJE), hoje=HOJE)
    build_silver(lake, settings)
    k = silver_key("produto", 24269, "produto.parquet")
    a = pq.read_table(io.BytesIO(lake.get(k))).to_pylist()
    lake.put(k, b"corrompido")
    build_silver(lake, settings)  # um único comando reconstrói
    assert pq.read_table(io.BytesIO(lake.get(k))).to_pylist() == a


def test_ptax_aceita_fechamento_ptax_do_bcb():
    """Formato real do BCB (12/11/2026): tipoBoletim = 'Fechamento PTAX'."""
    import json

    raw = json.dumps({"value": [
        {"paridadeCompra": 1.0, "paridadeVenda": 1.0, "cotacaoCompra": 5.5235, "cotacaoVenda": 5.5242,
         "dataHoraCotacao": "2026-11-09 13:11:18.845204", "tipoBoletim": "Intermediário"},
        {"paridadeCompra": 1.0, "paridadeVenda": 1.0, "cotacaoCompra": 5.5140, "cotacaoVenda": 5.5146,
         "dataHoraCotacao": "2026-11-09 13:11:19.041465", "tipoBoletim": "Fechamento PTAX"},
    ]}).encode()
    r = parse_ptax(raw, date(2026, 11, 9), "k")
    assert len(r) == 1
    assert r[0]["boletim"] == "Fechamento" and r[0]["cotacao_venda"] == 5.5146 and r[0]["cotacao_compra"] == 5.5140


def test_code_card_sem_numero_e_carta_nao_selado():
    """Dado real da ASC (14/11/2026): Code Card não tem 'Number', mas não é selado."""
    import json

    raw = json.dumps({"results": [
        {"productId": 10, "name": "Code Card - Ascended Heroes", "imageUrl": None, "url": None,
         "extendedData": [{"name": "Rarity", "value": "Code Card"}]},
        {"productId": 11, "name": "Ascended Heroes Booster Box", "imageUrl": None, "url": None, "extendedData": []},
    ]}).encode()
    rows = {r["product_id"]: r for r in parse_products(raw, 24541)}
    assert rows[10]["tipo_produto"] == "carta" and rows[10]["raridade"] == "Code Card"
    assert rows[11]["tipo_produto"] == "selado"
