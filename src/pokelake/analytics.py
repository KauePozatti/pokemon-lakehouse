"""As cinco perguntas de investimento. Funções puras sobre um DataFrame longo do fato de preço.

Convenções (ADR-005):
- Cartas com raridade 'Code Card' ficam fora das perguntas 1 a 5.
- "Um exemplar de cada carta" = um acabamento canônico por produto (Normal > Holofoil > Reverse
  Holofoil > demais, em ordem alfabética).
- Cestas são fixas (composição definida no primeiro dia da janela) e usam o último preço conhecido
  nos dias sem preço, sem gravar nada na silver.
- Filtros de preço mínimo são sempre em dólar, para a lista não mudar quando o câmbio muda.
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

PREF_ACABAMENTO = ["Normal", "Holofoil", "Reverse Holofoil"]
RARIDADES_BAIXAS = {"Common", "Uncommon", "Rare", "Promo", "Code Card"}  # "Double Rare em diante" = o resto


def load_prices(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Fato de preço enriquecido com as dimensões (lê as views fato_*/dim_* já registradas)."""
    df = con.execute(
        """SELECT f.data, f.product_id, f.group_id, f.acabamento, f.market_price, f.market_price_brl,
                  f.cotacao_venda, f.cotacao_compra,
                  p.nome, p.tipo_produto, p.categoria_selado, p.raridade, p.numero, p.image_url, p.url,
                  p.is_code_card, c.sigla, c.nome AS colecao
           FROM fato_preco_diario f
           JOIN dim_produto p ON p.product_id = f.product_id
           JOIN dim_colecao c ON c.group_id = f.group_id"""
    ).df()
    df["data"] = pd.to_datetime(df["data"])
    return df


def _col(moeda: str) -> str:
    return "market_price_brl" if moeda == "BRL" else "market_price"


def _cartas(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["tipo_produto"] == "carta") & (~df["is_code_card"].astype(bool))]


def canonical(df: pd.DataFrame) -> pd.DataFrame:
    """Um acabamento por carta (regra de 'um exemplar de cada carta')."""
    cartas = _cartas(df)
    rank = cartas["acabamento"].map({a: i for i, a in enumerate(PREF_ACABAMENTO)}).fillna(len(PREF_ACABAMENTO))
    pick = (
        cartas.assign(_r=rank)
        .sort_values(["product_id", "_r", "acabamento"])
        .drop_duplicates("product_id")[["product_id", "acabamento"]]
    )
    return cartas.merge(pick, on=["product_id", "acabamento"])


def _matriz(df: pd.DataFrame, col: str) -> pd.DataFrame:
    return df.pivot_table(index="data", columns=["product_id", "acabamento"], values=col, aggfunc="last").sort_index()


def indice_cesta(df: pd.DataFrame, col: str, inicio=None, agg: str = "sum") -> pd.Series:
    """Série do valor de uma cesta fixa (itens com preço no primeiro dia), com último preço conhecido."""
    if df.empty:
        return pd.Series(dtype=float)
    pv = _matriz(df.dropna(subset=[col]), col)
    if pv.empty:
        return pd.Series(dtype=float)
    pv = pv.reindex(pd.date_range(pv.index.min(), pv.index.max(), freq="D")).ffill()
    if inicio is not None:
        pv = pv[pv.index >= pd.Timestamp(inicio)]
    if pv.empty:
        return pd.Series(dtype=float)
    base = pv.columns[pv.iloc[0].notna()]
    pv = pv[base]
    if pv.shape[1] == 0:
        return pd.Series(dtype=float)
    return pv.sum(axis=1) if agg == "sum" else pv.mean(axis=1)


def _base100(s: pd.Series) -> pd.Series:
    return s / s.iloc[0] * 100 if len(s) and s.iloc[0] else s


# ---------------------------------------------------------------------------------- Pergunta 1
def decompor(usd_ini: float, usd_fim: float, ptax_ini: float, ptax_fim: float) -> dict:
    """(1 + r_brl) = (1 + r_usd) * (1 + r_cambio)  =>  r_brl = r_usd + r_cambio + r_usd*r_cambio."""
    r_usd = usd_fim / usd_ini - 1
    r_cambio = ptax_fim / ptax_ini - 1
    return {
        "var_brl": (usd_fim * ptax_fim) / (usd_ini * ptax_ini) - 1,
        "efeito_carta": r_usd,
        "efeito_cambio": r_cambio,
        "efeito_cruzado": r_usd * r_cambio,
    }


def q1_variacao(df: pd.DataFrame, group_id: int, min_usd: float = 1.0, top: int = 10, moeda: str = "BRL"):
    """Maiores valorizações e desvalorizações desde o início da coleta, por carta e acabamento."""
    d = _cartas(df[df["group_id"] == group_id])
    d = d[d["market_price"].notna() & d["cotacao_venda"].notna()].sort_values("data")
    chave = ["product_id", "acabamento"]
    meta = chave + ["nome", "raridade", "numero", "image_url", "url"]
    ini = d.groupby(chave).head(1)[meta + ["data", "market_price", "cotacao_venda"]].rename(
        columns={"data": "data_ini", "market_price": "usd_ini", "cotacao_venda": "ptax_ini"}
    )
    fim = d.groupby(chave).tail(1)[chave + ["data", "market_price", "cotacao_venda"]].rename(
        columns={"data": "data_fim", "market_price": "usd_fim", "cotacao_venda": "ptax_fim"}
    )
    m = ini.merge(fim, on=chave)
    m = m[(m["data_ini"] < m["data_fim"]) & (m["usd_ini"] >= min_usd)].copy()
    if m.empty:
        return m, m
    m["brl_ini"] = m["usd_ini"] * m["ptax_ini"]
    m["brl_fim"] = m["usd_fim"] * m["ptax_fim"]
    m["efeito_carta"] = m["usd_fim"] / m["usd_ini"] - 1
    m["efeito_cambio"] = m["ptax_fim"] / m["ptax_ini"] - 1
    m["efeito_cruzado"] = m["efeito_carta"] * m["efeito_cambio"]
    m["var_brl"] = m["brl_fim"] / m["brl_ini"] - 1
    chave_rank = "var_brl" if moeda == "BRL" else "efeito_carta"
    m = m.sort_values(chave_rank, ascending=False)
    return m.head(top).reset_index(drop=True), m.tail(top).sort_values(chave_rank).reset_index(drop=True)


# ---------------------------------------------------------------------------------- Pergunta 2
def q2_indices(df: pd.DataFrame, group_id: int, moeda: str = "BRL") -> pd.DataFrame:
    """Selado (média da cesta) x cartas Double Rare+ (soma da cesta), índice base 100."""
    col = _col(moeda)
    g = df[df["group_id"] == group_id]
    selados = g[(g["tipo_produto"] == "selado") & (~g["is_code_card"].astype(bool))]
    cartas = canonical(g)
    cartas = cartas[cartas["raridade"].notna() & ~cartas["raridade"].isin(RARIDADES_BAIXAS)]
    s = _base100(indice_cesta(selados, col, agg="mean")).rename("indice_selados")
    c = _base100(indice_cesta(cartas, col, agg="sum")).rename("indice_cartas")
    out = pd.concat([s, c], axis=1)
    out.index.name = "data"
    return out.reset_index()


# ---------------------------------------------------------------------------------- Pergunta 3
def q3_colecoes(df: pd.DataFrame, moeda: str = "BRL", inicio=None):
    """Valor de um exemplar de cada carta, por coleção, base 100 numa janela comum (+ PTAX base 100)."""
    col = _col(moeda)
    cartas = canonical(df)
    if cartas.empty:
        return pd.DataFrame(), pd.DataFrame()
    comum = cartas.groupby("group_id")["data"].min().max()
    inicio = max(pd.Timestamp(inicio), comum) if inicio is not None else comum
    linhas = []
    for gid, g in cartas.groupby("group_id"):
        v = indice_cesta(g, col, inicio=inicio, agg="sum")
        if v.empty:
            continue
        linhas.append(
            pd.DataFrame(
                {"data": v.index, "group_id": gid, "sigla": g["sigla"].iloc[0], "valor": v.values, "indice": _base100(v).values}
            )
        )
    colecoes = pd.concat(linhas, ignore_index=True) if linhas else pd.DataFrame()
    ptax = df.dropna(subset=["cotacao_venda"]).drop_duplicates("data").set_index("data")["cotacao_venda"].sort_index()
    ptax = ptax.reindex(pd.date_range(ptax.index.min(), ptax.index.max(), freq="D")).ffill()
    ptax = ptax[ptax.index >= inicio]
    ptax_df = pd.DataFrame({"data": ptax.index, "indice_ptax": _base100(ptax).values})
    return colecoes, ptax_df


# ---------------------------------------------------------------------------------- Pergunta 4
def q4_concentracao(df: pd.DataFrame, moeda: str = "BRL"):
    """Participação de cada raridade no valor e nº de cartas que somam 80% do valor (último preço)."""
    col = _col(moeda)
    cartas = canonical(df).dropna(subset=[col]).sort_values("data")
    ult = cartas.groupby("product_id").tail(1).copy()
    ult["raridade"] = ult["raridade"].fillna("Sem raridade")
    por_rar = ult.groupby(["group_id", "sigla", "raridade"])[col].sum().rename("valor").reset_index()
    por_rar["participacao"] = por_rar["valor"] / por_rar.groupby("group_id")["valor"].transform("sum")
    n80 = []
    for gid, g in ult.groupby("group_id"):
        v = g[col].sort_values(ascending=False)
        acum = v.cumsum() / v.sum()
        n80.append({"group_id": gid, "sigla": g["sigla"].iloc[0], "cartas_80pct": int((acum < 0.8).sum() + 1),
                    "total_cartas": len(v), "valor_total": float(v.sum())})
    return por_rar, pd.DataFrame(n80)


# ---------------------------------------------------------------------------------- Pergunta 5
def q5_risco_retorno(df: pd.DataFrame, min_usd: float = 5.0, moeda: str = "BRL", inicio=None) -> pd.DataFrame:
    """Retorno no período x volatilidade dos retornos diários, para cartas com preço inicial >= min_usd (US$)."""
    col = _col(moeda)
    cartas = canonical(df)
    if cartas.empty:
        return pd.DataFrame()
    comum = cartas.groupby("group_id")["data"].min().max()
    inicio = max(pd.Timestamp(inicio), comum) if inicio is not None else comum
    cartas = cartas[cartas["data"] >= inicio].dropna(subset=[col]).sort_values("data")
    linhas = []
    for pid, g in cartas.groupby("product_id"):
        if g["market_price"].iloc[0] < min_usd or len(g) < 4:
            continue
        serie = g[col].to_numpy()
        rets = serie[1:] / serie[:-1] - 1
        vol = float(np.std(rets, ddof=1))
        ret = float(serie[-1] / serie[0] - 1)
        r0 = g.iloc[0]
        linhas.append(
            {"product_id": pid, "nome": r0["nome"], "sigla": r0["sigla"], "group_id": r0["group_id"],
             "raridade": r0["raridade"], "image_url": r0["image_url"], "url": r0["url"],
             "retorno": ret, "volatilidade": vol, "retorno_por_risco": ret / vol if vol > 0 else np.nan,
             "preco_ini_usd": float(g["market_price"].iloc[0]), "observacoes": len(g)}
        )
    return pd.DataFrame(linhas)
