"""Desafio: R$ 1.000 em cartas e selados contra dólar parado e CDI.

Regras (ADR-006):
- Compra no 1º dia pela PTAX de VENDA; unidades inteiras; a sobra fica em caixa e rende CDI.
- Avaliação diária pelo valor de liquidação: unidades x preço x (1 - taxa_venda) x PTAX de COMPRA + caixa.
- A composição usa APENAS os preços do primeiro dia (sem informação do futuro).
- Produto sem preço no dia usa o último preço observado; o dia é marcado (itens_preco_carregado).
- CDI só rende em dia com taxa publicada (fim de semana/feriado = fator 1).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from pokelake.analytics import RARIDADES_BAIXAS

CARTEIRAS = ["selado", "cesta_raras", "propria", "dolar", "cdi"]


@dataclass(frozen=True)
class PortfolioConfig:
    capital: float = 1000.0
    taxa_venda: float = 0.15
    # cesta_raras
    n_cesta: int = 10
    brl_por_carta: float = 100.0
    # propria: cartas de raridade alta com preço intermediário, peso igual (ADR-006)
    propria_n: int = 20
    propria_min_usd: float = 3.0
    propria_max_usd: float = 50.0


# ----------------------------------------------------------------------------- composição (dia 0)
def _unidades(orcamento_brl: float, preco_usd: float, ptax_venda: float) -> tuple[int, float]:
    unit = preco_usd * ptax_venda
    if unit <= 0:
        return 0, 0.0
    n = math.floor(orcamento_brl / unit + 1e-9)
    return n, n * unit


def escolher_selado(d0: pd.DataFrame, ptax_venda: float | None = None, orcamento: float | None = None) -> pd.Series | None:
    """Booster box da coleção (sem 'case'); sem ele, o selado de maior preço com preço.

    Revisão (ADR-006): se a escolha acima NÃO CABE no orçamento (uma unidade custa mais que
    `orcamento` reais), usa o selado de maior preço cuja unidade caiba. Se nenhum couber,
    mantém a escolha original (0 unidades, tudo em caixa). Sem `ptax_venda`/`orcamento`,
    só aplica a regra original.
    """
    s = d0[(d0["tipo_produto"] == "selado") & d0["market_price"].notna()]
    if s.empty:
        return None
    nome = s["nome"].str.lower()
    box = s[nome.str.contains("booster box") & ~nome.str.contains("case")]
    if not box.empty:
        escolhido = box.assign(_n=box["nome"].str.len()).sort_values(["_n", "market_price"], ascending=[True, False]).iloc[0]
    else:
        escolhido = s.sort_values("market_price", ascending=False).iloc[0]
    if ptax_venda is None or orcamento is None:
        return escolhido
    if escolhido["market_price"] * ptax_venda <= orcamento:
        return escolhido
    cabem = s[s["market_price"] * ptax_venda <= orcamento]
    if cabem.empty:
        return escolhido
    return cabem.sort_values(["market_price", "product_id"], ascending=[False, True]).iloc[0]


def _top_cartas(d0: pd.DataFrame) -> pd.DataFrame:
    c = d0[(d0["tipo_produto"] == "carta") & (~d0["is_code_card"].astype(bool)) & d0["market_price"].notna()]
    return c.sort_values(["market_price", "product_id"], ascending=[False, True]).drop_duplicates("product_id")


def compor(d0: pd.DataFrame, ptax_venda: float, cfg: PortfolioConfig) -> tuple[dict, dict]:
    """Devolve ({carteira: [posicoes]}, {carteira: caixa_inicial_brl}). Só usa o dia 0."""
    pos: dict[str, list[dict]] = {k: [] for k in ("selado", "cesta_raras", "propria")}
    caixa: dict[str, float] = {}

    def comprar(carteira: str, linhas: pd.DataFrame, orcamento: float):
        gasto = 0.0
        for _, r in linhas.iterrows():
            n, custo = _unidades(orcamento, r["market_price"], ptax_venda)
            gasto += custo
            pos[carteira].append(
                {"carteira": carteira, "product_id": int(r["product_id"]), "acabamento": r["acabamento"],
                 "nome": r["nome"], "unidades": int(n), "preco_compra_usd": float(r["market_price"]),
                 "custo_brl": float(custo)}
            )
        return gasto

    sel = escolher_selado(d0, ptax_venda, cfg.capital)
    gasto = comprar("selado", sel.to_frame().T if sel is not None else d0.iloc[0:0], cfg.capital)
    caixa["selado"] = cfg.capital - gasto

    top = _top_cartas(d0).head(cfg.n_cesta)
    gasto = comprar("cesta_raras", top, cfg.brl_por_carta)
    caixa["cesta_raras"] = cfg.capital - gasto

    # propria (ADR-006, revisado): orçamento fixo por carta; só entram cartas cuja unidade CABE nele.
    orcamento_carta = cfg.capital / cfg.propria_n
    c = _top_cartas(d0)
    c = c[
        c["raridade"].notna()
        & ~c["raridade"].isin(RARIDADES_BAIXAS)
        & c["market_price"].between(cfg.propria_min_usd, cfg.propria_max_usd)
        & ((c["market_price"] * ptax_venda) <= orcamento_carta)
    ].head(cfg.propria_n)
    gasto = comprar("propria", c, orcamento_carta)
    caixa["propria"] = cfg.capital - gasto
    return pos, caixa


# ----------------------------------------------------------------------------- simulação
def simulate(prices: pd.DataFrame, cambio: pd.DataFrame, group_id: int, cfg: PortfolioConfig):
    """prices: fato enriquecido (analytics.load_prices). cambio: fato_cambio_diario.

    Devolve (curvas, composicao). curvas: data, group_id, carteira, valor_brl, retorno_acumulado,
    taxa_venda, itens_preco_carregado.
    """
    p = prices[(prices["group_id"] == group_id) & prices["market_price"].notna()].copy()
    p["data"] = pd.to_datetime(p["data"])
    cam = cambio.copy()
    cam["data"] = pd.to_datetime(cam["data"])
    cam = cam.set_index("data").sort_index()
    cam = cam[cam["cotacao_venda"].notna()]
    d0 = next((d for d in sorted(p["data"].unique()) if d in cam.index), None)
    if d0 is None:
        raise ValueError("Sem dia com preço e PTAX conhecida: nada a simular")
    d0 = pd.Timestamp(d0)
    datas = cam.index[(cam.index >= d0) & (cam.index <= p["data"].max())]
    cam = cam.loc[datas]

    venda0 = float(cam.loc[d0, "cotacao_venda"])
    pos, caixa0 = compor(p[p["data"] == d0], venda0, cfg)

    fator = 1 + cam["cdi_taxa_dia"].astype(float) / 100
    fator.iloc[0] = 1.0  # o dia da compra não rende
    acum = fator.cumprod()
    compra = cam["cotacao_compra"].astype(float)

    pv = (
        p.pivot_table(index="data", columns=["product_id", "acabamento"], values="market_price", aggfunc="last")
        .reindex(datas)
    )
    observado = pv.notna()
    ff = pv.ffill()

    curvas = []
    comp_rows = []

    def registra(nome: str, valor: pd.Series, carregados: pd.Series | None = None):
        carregados = carregados if carregados is not None else pd.Series(0, index=datas)
        curvas.append(
            pd.DataFrame(
                {
                    "data": datas.date,
                    "group_id": group_id,
                    "carteira": nome,
                    "valor_brl": valor.values,
                    "retorno_acumulado": (valor / cfg.capital - 1).values,
                    "taxa_venda": cfg.taxa_venda,
                    "itens_preco_carregado": carregados.values,
                }
            )
        )

    for nome in ("selado", "cesta_raras", "propria"):
        itens = [x for x in pos[nome] if x["unidades"] > 0]
        valor_itens = pd.Series(0.0, index=datas)
        carreg = pd.Series(0, index=datas)
        for x in itens:
            kk = (x["product_id"], x["acabamento"])
            valor_itens = valor_itens + x["unidades"] * ff[kk]
            carreg = carreg + ((~observado[kk]) & ff[kk].notna()).astype(int)
        liquido = valor_itens * (1 - cfg.taxa_venda) * compra + caixa0[nome] * acum
        registra(nome, liquido, carreg)
        for x in pos[nome]:
            comp_rows.append({**x, "caixa_inicial_brl": caixa0[nome], "group_id": group_id})

    registra("dolar", (cfg.capital / venda0) * compra)  # converte pela PTAX de venda, liquida pela de compra
    registra("cdi", cfg.capital * acum)

    curvas_df = pd.concat(curvas, ignore_index=True)
    comp_df = pd.DataFrame(comp_rows)
    return curvas_df, comp_df


def metricas(curvas: pd.DataFrame) -> pd.DataFrame:
    """Retorno acumulado, excesso sobre o CDI, perda máxima e dias com preço carregado, por carteira."""
    linhas = []
    cdi_ret = curvas[curvas["carteira"] == "cdi"].sort_values("data")["retorno_acumulado"].iloc[-1]
    for nome, g in curvas.groupby("carteira"):
        g = g.sort_values("data")
        v = g["valor_brl"].to_numpy()
        pico = np.maximum.accumulate(v)
        linhas.append(
            {
                "carteira": nome,
                "valor_final_brl": float(v[-1]),
                "retorno_acumulado": float(g["retorno_acumulado"].iloc[-1]),
                "excesso_sobre_cdi": float(g["retorno_acumulado"].iloc[-1] - cdi_ret),
                "perda_maxima": float((v / pico - 1).min()),
                "dias_preco_carregado": int((g["itens_preco_carregado"] > 0).sum()),
            }
        )
    out = pd.DataFrame(linhas)
    out["carteira"] = pd.Categorical(out["carteira"], CARTEIRAS, ordered=True)
    return out.sort_values("carteira").reset_index(drop=True)


def placar_turma(carteiras: pd.DataFrame) -> dict:
    """Placar a partir de gold_turma/carteira (todas as coleções, último dia de cada uma)."""
    ult = carteiras.sort_values("data").groupby(["group_id", "carteira"]).tail(1)
    ret = ult.pivot(index="group_id", columns="carteira", values="retorno_acumulado")
    dd = {}
    for (gid, cart), g in carteiras.groupby(["group_id", "carteira"]):
        v = g.sort_values("data")["valor_brl"].to_numpy()
        dd.setdefault(gid, {})[cart] = float((v / np.maximum.accumulate(v) - 1).min())
    dd = pd.DataFrame(dd).T
    res = {"colecoes": int(len(ret))}
    if {"selado", "cdi"} <= set(ret.columns):
        res["selado_ganhou_do_cdi"] = int((ret["selado"] > ret["cdi"]).sum())
    if {"cesta_raras", "dolar"} <= set(ret.columns):
        res["cesta_ganhou_do_dolar"] = int((ret["cesta_raras"] > ret["dolar"]).sum())
    cartas = [c for c in ("selado", "cesta_raras", "propria") if c in dd.columns]
    if cartas:
        menor = dd[cartas].min(axis=1)
        res["menor_perda_maxima_group_id"] = int(menor.idxmax())
        res["menor_perda_maxima"] = float(menor.max())
    res["retornos"] = ret
    return res
