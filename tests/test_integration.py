"""Integração: bruto sintético -> silver -> gold -> perguntas -> carteiras (backend local)."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from pokelake.analytics import load_prices, q1_variacao, q2_indices, q3_colecoes, q4_concentracao, q5_risco_retorno
from pokelake.config import Settings
from pokelake.db import connect
from pokelake.demo import seed_demo
from pokelake.pipeline import _gold_views, rebuild
from pokelake.portfolio import placar_turma
from pokelake.storage import LocalLake


@pytest.fixture(scope="module")
def mundo(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("lake")
    s = Settings(backend="local", local_root=Path(raiz), sigla="DRI", group_id=24269, responsavel="Aluno")
    lake = LocalLake(s)
    grupos = seed_demo(lake, s, fim=date(2026, 11, 20), n_dias=30)
    rebuild(lake, s, grupos)
    con = _gold_views(connect(lake, s), lake, s)
    return s, lake, con, load_prices(con)


def test_gold_tem_o_modelo_estrela(mundo):
    _, _, con, _ = mundo
    tabelas = {r[0] for r in con.execute("SHOW TABLES").fetchall()} | {r[0] for r in con.execute("SELECT view_name FROM duckdb_views() WHERE NOT internal").fetchall()}
    assert {"fato_preco_diario", "dim_produto", "dim_colecao", "dim_data", "dim_acabamento", "fato_cambio_diario"} <= tabelas


def test_demo_recusa_s3(tmp_path):
    from pokelake.storage import BaseLake

    class Falso(BaseLake):
        kind = "s3"

    with pytest.raises(RuntimeError):
        seed_demo(Falso(), Settings(backend="s3"))


def test_pergunta_1(mundo):
    s, _, _, df = mundo
    ganhos, perdas = q1_variacao(df, s.group_id, min_usd=1.0)
    assert len(ganhos) == 10 and len(perdas) == 10
    assert ganhos["var_brl"].is_monotonic_decreasing
    assert (ganhos["usd_ini"] >= 1.0).all()
    soma = (1 + ganhos["efeito_carta"]) * (1 + ganhos["efeito_cambio"]) - 1
    pd.testing.assert_series_equal(soma, ganhos["var_brl"], check_names=False)
    assert not ganhos["nome"].str.contains("Code").any()


def test_pergunta_2_indices_base_100(mundo):
    s, _, _, df = mundo
    q2 = q2_indices(df, s.group_id)
    assert q2["indice_selados"].iloc[0] == pytest.approx(100) and q2["indice_cartas"].iloc[0] == pytest.approx(100)


def test_pergunta_3_janela_comum_e_ptax(mundo):
    _, _, _, df = mundo
    col, ptax = q3_colecoes(df)
    assert col["sigla"].nunique() == 3
    primeiro = col.groupby("sigla")["data"].min()
    assert primeiro.nunique() == 1  # mesma janela para todas
    assert ptax["indice_ptax"].iloc[0] == pytest.approx(100)


def test_pergunta_4_participacoes_somam_100(mundo):
    _, _, _, df = mundo
    por_rar, n80 = q4_concentracao(df)
    assert por_rar.groupby("group_id")["participacao"].sum().round(6).eq(1).all()
    assert (n80["cartas_80pct"] <= n80["total_cartas"]).all()


def test_pergunta_5_filtro_de_preco(mundo):
    _, _, _, df = mundo
    r5 = q5_risco_retorno(df, min_usd=5.0)
    assert not r5.empty and (r5["preco_ini_usd"] >= 5.0).all() and (r5["volatilidade"] >= 0).all()


def test_carteiras_no_contrato_comum(mundo):
    s, lake, con, _ = mundo
    c = con.execute(f"SELECT * FROM read_parquet('{lake.uri('gold_turma/carteira/*/*.parquet')}', hive_partitioning=false)").df()
    assert list(c.columns) == ["data", "group_id", "carteira", "valor_brl", "retorno_acumulado", "taxa_venda"]
    assert set(c["carteira"]) == {"selado", "cesta_raras", "propria", "dolar", "cdi"}
    pl = placar_turma(c)
    assert pl["colecoes"] == 1
