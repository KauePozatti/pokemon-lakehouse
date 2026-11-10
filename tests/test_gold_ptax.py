"""Regra da última cotação conhecida: fim de semana e feriado (semana de 09/10 a 13/10/2026)."""
from datetime import date, datetime

from pokelake.db import connect
from pokelake.gold import build_gold_tables
from pokelake.keys import silver_key
from tests.conftest import put_parquet

GID = 24269


def _prepara(lake):
    put_parquet(lake, silver_key("colecao", GID, "colecao.parquet"), "colecao",
                [{"group_id": GID, "nome": "SV10: Destined Rivals", "sigla": "DRI", "data_lancamento": date(2025, 5, 30), "responsavel": "t"}])
    put_parquet(lake, silver_key("produto", GID, "produto.parquet"), "produto",
                [{"product_id": 1, "group_id": GID, "nome": "Carta", "tipo_produto": "carta", "raridade": "Rare", "numero": "1/1", "image_url": None, "url": None}])
    cambio = [
        {"data": date(2026, 10, 9), "cotacao_compra": 5.00, "cotacao_venda": 5.10, "data_hora_cotacao": datetime(2026, 10, 9, 13, 0), "boletim": "Fechamento", "chave_raw": "k"},
        {"data": date(2026, 10, 13), "cotacao_compra": 5.20, "cotacao_venda": 5.30, "data_hora_cotacao": datetime(2026, 10, 13, 13, 0), "boletim": "Fechamento", "chave_raw": "k"},
    ]
    put_parquet(lake, silver_key("cambio_diario", GID, "cambio.parquet"), "cambio_diario", cambio)
    put_parquet(lake, silver_key("cdi_diario", GID, "cdi.parquet"), "cdi_diario",
                [{"data": date(2026, 10, 9), "taxa_dia": 0.05, "chave_raw": "k"}, {"data": date(2026, 10, 13), "taxa_dia": 0.05, "chave_raw": "k"}])
    for dia in range(9, 14):
        d = date(2026, 10, dia)
        put_parquet(lake, silver_key("preco_diario", GID, "preco.parquet", d), "preco_diario",
                    [{"data": d, "product_id": 1, "group_id": GID, "acabamento": "Holofoil", "market_price": 10.0, "low_price": 9.0,
                      "mid_price": 10.0, "high_price": 12.0, "moeda": "USD", "fonte": "t", "chave_raw": "k"}])


def test_fim_de_semana_e_feriado_usam_ptax_de_09_10(lake, settings):
    _prepara(lake)
    con = connect(lake, settings)
    build_gold_tables(con, lake, settings)
    rows = {r[0]: r for r in con.execute(
        "SELECT data, data_ptax, cotacao_venda, market_price_brl FROM fato_preco_diario ORDER BY data").fetchall()}
    for dia in (9, 10, 11, 12):  # sex, sáb, dom e o feriado de 12/10
        assert rows[date(2026, 10, dia)][1] == date(2026, 10, 9)
        assert rows[date(2026, 10, dia)][2] == 5.10
        assert rows[date(2026, 10, dia)][3] == 10.0 * 5.10
    assert rows[date(2026, 10, 13)][1] == date(2026, 10, 13)  # dia com boletim usa o próprio


def test_nunca_usa_cotacao_posterior(lake, settings):
    _prepara(lake)
    con = connect(lake, settings)
    build_gold_tables(con, lake, settings)
    assert con.execute("SELECT count(*) FROM fato_preco_diario WHERE data_ptax > data").fetchone()[0] == 0


def test_cdi_zero_em_dia_sem_taxa(lake, settings):
    _prepara(lake)
    con = connect(lake, settings)
    build_gold_tables(con, lake, settings)
    cdi = {r[0]: r[1] for r in con.execute("SELECT data, cdi_taxa_dia FROM fato_cambio_diario").fetchall()}
    assert cdi[date(2026, 10, 10)] == 0.0 and cdi[date(2026, 10, 11)] == 0.0 and cdi[date(2026, 10, 12)] == 0.0
    assert cdi[date(2026, 10, 9)] == 0.05 and cdi[date(2026, 10, 13)] == 0.05
