from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from pokelake.analytics import decompor
from pokelake.portfolio import PortfolioConfig, compor, escolher_selado, metricas, simulate

GID = 24269


def _prices(dias: int = 6, extra_futuro: bool = False) -> pd.DataFrame:
    base = pd.Timestamp("2026-10-09")  # sexta
    cat = [  # product_id, nome, tipo, raridade, preço USD
        (1, "Chase", "carta", "Special Illustration Rare", 100.0),
        (2, "Media", "carta", "Ultra Rare", 8.0),
        (3, "Barata", "carta", "Common", 0.5),
        (4, "X Booster Box", "selado", None, 130.0),
        (5, "X Booster Box Case", "selado", None, 780.0),
        (6, "Code", "carta", "Code Card", 0.1),
    ]
    rows = []
    for i in range(dias):
        d = base + pd.Timedelta(days=i)
        for pid, nome, tipo, rar, p in cat:
            if pid == 2 and i == 2:
                continue  # sem preço neste dia -> preço carregado
            rows.append({"data": d, "product_id": pid, "group_id": GID, "acabamento": "Holofoil" if tipo == "carta" else "Normal",
                         "market_price": p * (1 + 0.01 * i), "nome": nome, "tipo_produto": tipo, "raridade": rar,
                         "is_code_card": rar == "Code Card"})
    return pd.DataFrame(rows)


def _dia0(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["data"] == pd.Timestamp("2026-10-09")]


def _cambio(dias: int = 6) -> pd.DataFrame:
    base = date(2026, 10, 9)
    out = []
    for i in range(dias):
        d = base + timedelta(days=i)
        util = d.weekday() < 5
        out.append({"data": d, "cotacao_compra": 5.0, "cotacao_venda": 5.1, "cdi_taxa_dia": 0.05 if util else 0.0})
    return pd.DataFrame(out)


def test_unidades_inteiras_e_sobra_em_caixa():
    pos, caixa = compor(_dia0(_prices()), 5.1, PortfolioConfig())
    for carteira, itens in pos.items():
        assert all(isinstance(x["unidades"], int) for x in itens)
        gasto = sum(x["custo_brl"] for x in itens)
        assert gasto + caixa[carteira] == pytest.approx(1000.0)
    # booster box (US$130 * 5,1 = R$663): 1 unidade, sobra R$337
    assert pos["selado"][0]["unidades"] == 1 and caixa["selado"] == pytest.approx(1000 - 130 * 5.1)
    # carta de US$100 custa R$510 > R$100 por carta: 0 unidades, o R$100 vira caixa
    chase = [x for x in pos["cesta_raras"] if x["product_id"] == 1][0]
    assert chase["unidades"] == 0


def test_selado_escolhe_box_sem_case_e_ignora_code_card_na_cesta():
    d0 = _dia0(_prices())
    assert escolher_selado(d0)["nome"] == "X Booster Box"
    pos, _ = compor(d0, 5.1, PortfolioConfig())
    assert 6 not in [x["product_id"] for x in pos["cesta_raras"]]


def test_composicao_nao_usa_informacao_do_futuro():
    curto, longo = _prices(dias=2), _prices(dias=6)
    longo.loc[longo["data"] > pd.Timestamp("2026-10-09"), "market_price"] *= 50  # o futuro muda drasticamente
    c1 = simulate(curto, _cambio(2), GID, PortfolioConfig())[1]
    c2 = simulate(longo, _cambio(6), GID, PortfolioConfig())[1]
    cols = ["carteira", "product_id", "acabamento", "unidades"]
    pd.testing.assert_frame_equal(c1[cols].reset_index(drop=True), c2[cols].reset_index(drop=True))


def test_cdi_so_rende_em_dia_util_e_dia_da_compra_nao_rende():
    curvas, _ = simulate(_prices(), _cambio(), GID, PortfolioConfig())
    cdi = curvas[curvas["carteira"] == "cdi"].set_index("data")["valor_brl"]
    assert cdi[date(2026, 10, 9)] == 1000.0                       # dia da compra
    assert cdi[date(2026, 10, 10)] == cdi[date(2026, 10, 9)]      # sábado
    assert cdi[date(2026, 10, 11)] == cdi[date(2026, 10, 10)]     # domingo
    assert cdi[date(2026, 10, 12)] == pytest.approx(1000 * 1.0005)  # segunda: rende


def test_dolar_compra_na_venda_e_liquida_na_compra():
    curvas, _ = simulate(_prices(), _cambio(), GID, PortfolioConfig())
    d = curvas[curvas["carteira"] == "dolar"].set_index("data")["valor_brl"]
    assert d[date(2026, 10, 9)] == pytest.approx(1000 / 5.1 * 5.0)  # spread compra/venda


def test_preco_carregado_e_marcado_e_usa_ultimo_preco_observado():
    # Só o produto 2 (Ultra Rare, US$8) entra na carteira "propria" e ele não tem preço em 11/10.
    curvas, comp = simulate(_prices(), _cambio(), GID, PortfolioConfig())
    propria = curvas[curvas["carteira"] == "propria"].set_index("data")
    assert propria.loc[date(2026, 10, 11), "itens_preco_carregado"] == 1
    assert propria.loc[date(2026, 10, 10), "itens_preco_carregado"] == 0
    unidades = comp[(comp["carteira"] == "propria") & (comp["product_id"] == 2)]["unidades"].iloc[0]
    assert unidades > 0
    # valor de 11/10 = último preço observado (10/10), não um preço inventado nem zero
    p10 = 8.0 * 1.01
    esperado_itens = unidades * p10 * (1 - 0.15) * 5.0
    caixa = comp[(comp["carteira"] == "propria")]["caixa_inicial_brl"].iloc[0]
    cdi_acum = 1.0  # sáb e dom: sem juros
    assert propria.loc[date(2026, 10, 11), "valor_brl"] == pytest.approx(esperado_itens + caixa * cdi_acum)
    m = metricas(curvas).set_index("carteira")
    assert m.loc["propria", "dias_preco_carregado"] >= 1
    assert set(m.index.astype(str)) == {"selado", "cesta_raras", "propria", "dolar", "cdi"}


def test_taxa_de_venda_reduz_valor_das_carteiras_de_cartas():
    com, _ = simulate(_prices(), _cambio(), GID, PortfolioConfig(taxa_venda=0.15))
    sem, _ = simulate(_prices(), _cambio(), GID, PortfolioConfig(taxa_venda=0.0))
    ult = lambda c, n: c[c["carteira"] == n]["valor_brl"].iloc[-1]  # noqa: E731
    assert ult(com, "selado") < ult(sem, "selado")
    assert ult(com, "dolar") == pytest.approx(ult(sem, "dolar"))  # dólar não paga taxa de marketplace


def test_perda_maxima_e_excesso_sobre_cdi():
    curvas, _ = simulate(_prices(), _cambio(), GID, PortfolioConfig())
    m = metricas(curvas).set_index("carteira")
    assert m.loc["cdi", "excesso_sobre_cdi"] == 0 and m.loc["cdi", "perda_maxima"] == 0
    assert (m["perda_maxima"] <= 0).all()


def test_decomposicao_da_variacao_em_reais():
    r = decompor(100, 110, 5.00, 5.25)  # exemplo da página do projeto
    assert r["efeito_carta"] == pytest.approx(0.10)
    assert r["efeito_cambio"] == pytest.approx(0.05)
    assert r["efeito_cruzado"] == pytest.approx(0.005)
    assert r["var_brl"] == pytest.approx(0.155)
    assert (1 + r["efeito_carta"]) * (1 + r["efeito_cambio"]) - 1 == pytest.approx(r["var_brl"])


def test_selado_cai_para_o_que_cabe_quando_a_box_passa_do_orcamento():
    d0 = _dia0(_prices()).copy()
    d0.loc[d0["product_id"] == 4, "market_price"] = 302.69  # box: R$ 1.543 > R$ 1.000
    etb = d0[d0["product_id"] == 4].iloc[0].copy()
    etb["product_id"], etb["nome"], etb["market_price"] = 7, "X Elite Trainer Box", 55.0
    d0 = pd.concat([d0, etb.to_frame().T], ignore_index=True)
    d0["market_price"] = d0["market_price"].astype(float)
    escolhido = escolher_selado(d0, 5.1, 1000.0)
    assert escolhido["nome"] == "X Elite Trainer Box"          # o mais caro que cabe
    pos, caixa = compor(d0, 5.1, PortfolioConfig())
    assert pos["selado"][0]["unidades"] == 3                   # 55*5,1 = R$280,5 -> 3 unidades
    assert caixa["selado"] == pytest.approx(1000 - 3 * 55 * 5.1)


def test_selado_sem_nada_que_caiba_mantem_a_escolha_original():
    d0 = _dia0(_prices()).copy()
    d0.loc[d0["tipo_produto"] == "selado", "market_price"] = 500.0
    assert escolher_selado(d0, 5.1, 1000.0)["nome"] == "X Booster Box"
    pos, caixa = compor(d0, 5.1, PortfolioConfig())
    assert pos["selado"][0]["unidades"] == 0 and caixa["selado"] == pytest.approx(1000.0)


def test_propria_so_inclui_cartas_cuja_unidade_cabe_no_orcamento():
    d0 = _dia0(_prices()).copy()
    caro = d0[d0["product_id"] == 2].iloc[0].copy()  # US$ 8 -> R$ 40,8: cabe em R$ 50
    caro["product_id"], caro["nome"], caro["market_price"] = 8, "Carta Cara Demais", 30.0  # R$ 153: não cabe
    d0 = pd.concat([d0, caro.to_frame().T], ignore_index=True)
    d0["market_price"] = d0["market_price"].astype(float)
    pos, _ = compor(d0, 5.1, PortfolioConfig())
    ids = [x["product_id"] for x in pos["propria"]]
    assert 2 in ids and 8 not in ids
    assert all(x["unidades"] >= 1 for x in pos["propria"])


def test_selado_ignora_code_card_mesmo_classificado_como_selado():
    base = _dia0(_prices())
    modelo = base[base["product_id"] == 4].iloc[0]
    cc = modelo.copy(); cc["product_id"], cc["nome"], cc["market_price"] = 9, "Code Card X", 500.0
    cc["raridade"], cc["is_code_card"] = "Code Card", True
    bundle = modelo.copy(); bundle["product_id"], bundle["nome"], bundle["market_price"] = 10, "X Booster Bundle", 28.0
    bundle["raridade"], bundle["is_code_card"] = None, False
    d0 = pd.concat([cc.to_frame().T, bundle.to_frame().T], ignore_index=True)
    d0["market_price"] = d0["market_price"].astype(float)
    d0["is_code_card"] = d0["is_code_card"].astype(bool)
    assert escolher_selado(d0)["nome"] == "X Booster Bundle"
