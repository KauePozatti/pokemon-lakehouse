from datetime import date

import pytest

from pokelake.collect import DadoDefasadoError, collect, colecoes_ocupadas
from pokelake.keys import raw_key
from tests.conftest import FakeFetcher

HOJE = date(2026, 11, 9)  # segunda-feira


def test_coleta_grava_bruto_original(lake, settings):
    f = FakeFetcher(HOJE)
    rel = collect(lake, settings, fetcher=f, hoje=HOJE)
    assert rel["tcgplayer"][raw_key("tcgplayer", 24269, HOJE, "products.json")] == "gravado"
    assert lake.exists(raw_key("tcgplayer", 24269, HOJE, "prices.json"))
    assert lake.exists(raw_key("bcb_cdi", 24269, HOJE, "cdi.json"))
    # PTAX do dia + 5 dias de lookback, inclusive fim de semana (resposta vazia gravada como veio)
    assert len(rel["bcb_ptax"]) == 6


def test_idempotencia_segunda_execucao_nao_grava_nem_chama(lake, settings):
    collect(lake, settings, fetcher=FakeFetcher(HOJE), hoje=HOJE)
    antes = {k: lake.get(k) for k in lake.list_keys("raw/")}
    f2 = FakeFetcher(HOJE)
    rel = collect(lake, settings, fetcher=f2, hoje=HOJE)
    assert f2.chamadas == []  # nenhuma requisição repetida
    assert all(v == "ja_existia" for fonte in rel.values() for v in fonte.values())
    assert {k: lake.get(k) for k in lake.list_keys("raw/")} == antes  # nada sobrescrito


def test_bruto_nunca_e_sobrescrito(lake):
    assert lake.put_if_absent("raw/x/a.json", b"original") is True
    assert lake.put_if_absent("raw/x/a.json", b"alterado") is False
    assert lake.get("raw/x/a.json") == b"original"


def test_dado_defasado_nao_e_gravado(lake, settings):
    f = FakeFetcher(date(2026, 11, 8))  # TCGCSV parou ontem
    with pytest.raises(DadoDefasadoError):
        collect(lake, settings, fetcher=f, hoje=HOJE)
    assert lake.list_keys("raw/tcgplayer/") == []


def test_colecoes_ocupadas(lake, settings):
    collect(lake, settings, fetcher=FakeFetcher(HOJE), hoje=HOJE)
    assert colecoes_ocupadas(lake) == [24269]
