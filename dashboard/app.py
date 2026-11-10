"""Dashboard: cartas Pokémon como ativo de coleção.

Rodar:  streamlit run dashboard/app.py
Lê o gold do próprio aluno (construído sobre a silver de toda a turma) e o placar em gold_turma/.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from pokelake.analytics import (
    decompor,
    load_prices,
    q1_variacao,
    q2_indices,
    q3_colecoes,
    q4_concentracao,
    q5_risco_retorno,
)
from pokelake.config import load_settings
from pokelake.db import connect, read_parquet_sql
from pokelake.keys import GOLD_TABLES, gold_key
from pokelake.portfolio import CARTEIRAS, metricas, placar_turma
from pokelake.storage import make_lake

st.set_page_config(page_title="Cartas Pokémon como ativo", page_icon="🃏", layout="wide")

NOMES_CARTEIRA = {
    "selado": "Selado (booster box)",
    "cesta_raras": "Cesta das 10 mais caras",
    "propria": "Carteira própria",
    "dolar": "Dólar parado",
    "cdi": "CDI",
}


@st.cache_resource(show_spinner="Conectando ao data lake...")
def _conn():
    s = load_settings()
    lake = make_lake(s)
    con = connect(lake, s)
    for t in GOLD_TABLES:
        con.execute(f"CREATE OR REPLACE VIEW {t} AS SELECT * FROM {read_parquet_sql(lake.uri(gold_key(s.group_id, t)))}")
    return s, lake, con


@st.cache_data(ttl=1800, show_spinner="Lendo preços...")
def _precos() -> pd.DataFrame:
    _, _, con = _conn()
    return load_prices(con)


@st.cache_data(ttl=1800)
def _cambio() -> pd.DataFrame:
    _, _, con = _conn()
    return con.execute("SELECT * FROM fato_cambio_diario ORDER BY data").df()


@st.cache_data(ttl=1800)
def _carteira_gold(nome: str) -> pd.DataFrame:
    s, lake, con = _conn()
    return con.execute(f"SELECT * FROM {read_parquet_sql(lake.uri(gold_key(s.group_id, nome)))}").df()


@st.cache_data(ttl=1800)
def _carteira_turma() -> pd.DataFrame:
    _, lake, con = _conn()
    uri = lake.uri("gold_turma/carteira/*/*.parquet")
    return con.execute(f"SELECT * FROM {read_parquet_sql(uri)}").df()


def pct(x: float) -> str:
    return f"{x:+.1%}"


def brl(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def grade_cartas(df: pd.DataFrame, moeda: str):
    cols = st.columns(5)
    for i, r in df.iterrows():
        with cols[i % 5]:
            if r["image_url"]:
                st.image(r["image_url"], width="stretch")
            st.markdown(f"**[{r['nome']}]({r['url']})**  \n{r['acabamento']} · {r['raridade'] or '—'}")
            ini, fim = (r["brl_ini"], r["brl_fim"]) if moeda == "BRL" else (r["usd_ini"], r["usd_fim"])
            simb = "R$" if moeda == "BRL" else "US$"
            st.caption(f"{simb} {ini:,.2f} → {simb} {fim:,.2f}")
            st.markdown(f"**{pct(r['var_brl'] if moeda == 'BRL' else r['efeito_carta'])}**")
            st.caption(
                f"carta {pct(r['efeito_carta'])} · câmbio {pct(r['efeito_cambio'])} · cruzado {pct(r['efeito_cruzado'])}"
            )


try:
    s, lake, con = _conn()
    df = _precos()
    cambio = _cambio()
except Exception as e:  # noqa: BLE001
    st.error(f"Não consegui ler o gold: {e}")
    st.info("Rode antes `python -m pokelake rebuild` (ou `python -m pokelake demo` para testar com dados sintéticos).")
    st.stop()

if df.empty:
    st.warning("O gold está vazio. Rode a coleta e o rebuild.")
    st.stop()

st.title("🃏 Cartas Pokémon como ativo de coleção")
if "demo" in str(s.local_root).lower() or df["nome"].str.startswith("DEMO").any():
    st.warning("Dados SINTÉTICOS de demonstração. Não use para decidir nada.")

with st.sidebar:
    st.header("Filtros")
    moeda = st.radio("Moeda", ["BRL", "USD"], horizontal=True, help="Os filtros de preço mínimo são sempre em US$.")
    colecoes = df[["group_id", "sigla", "colecao"]].drop_duplicates().sort_values("sigla")
    opcoes = dict(zip(colecoes["sigla"], colecoes["group_id"]))
    padrao = list(opcoes).index(s.sigla) if s.sigla in opcoes else 0
    sigla_sel = st.selectbox("Minha coleção", list(opcoes), index=padrao)
    gid = int(opcoes[sigla_sel])
    datas = df["data"]
    st.caption(f"Série: {datas.min():%d/%m/%Y} a {datas.max():%d/%m/%Y} · {datas.nunique()} dias com preço")
    ult = cambio.dropna(subset=["cotacao_venda"]).iloc[-1]
    st.caption(f"PTAX aplicada em {pd.Timestamp(ult['data']):%d/%m/%Y}: venda {ult['cotacao_venda']:.4f} (boletim de {pd.Timestamp(ult['data_ptax']):%d/%m})")

t1, t2, t3, t4, t5, tc, tp, tq = st.tabs(
    ["1 · Valorização", "2 · Selado × cartas", "3 · Coleções", "4 · Concentração", "5 · Risco × retorno",
     "💰 Carteira R$ 1.000", "🏆 Placar da turma", "🔎 Qualidade dos dados"]
)

with t1:
    st.subheader("Quais cartas da minha coleção mais valorizaram e mais desvalorizaram?")
    min_usd = st.slider("Preço inicial mínimo (US$)", 0.0, 20.0, 1.0, 0.5, key="q1min")
    ganhos, perdas = q1_variacao(df, gid, min_usd=min_usd, moeda=moeda)
    if ganhos.empty:
        st.info("Ainda não há duas observações por carta para calcular variação.")
    else:
        st.markdown("#### 📈 Maiores valorizações")
        grade_cartas(ganhos, moeda)
        st.markdown("#### 📉 Maiores desvalorizações")
        grade_cartas(perdas, moeda)
        st.caption(
            "Variação em R$ = (1 + carta) × (1 + câmbio) − 1. Considera só cartas com preço inicial ≥ US$ "
            f"{min_usd:.2f}; Code Cards ficam de fora. Período: {ganhos['data_ini'].min():%d/%m} a {ganhos['data_fim'].max():%d/%m}."
        )
        ex = ganhos.iloc[0]
        chk = decompor(ex["usd_ini"], ex["usd_fim"], ex["ptax_ini"], ex["ptax_fim"])
        st.caption(f"Conferência: {ex['nome']} → {pct(chk['var_brl'])} = carta {pct(chk['efeito_carta'])} + câmbio {pct(chk['efeito_cambio'])} + cruzado {pct(chk['efeito_cruzado'])}.")

with t2:
    st.subheader("Na minha coleção, o selado guardou valor melhor que as cartas avulsas?")
    q2 = q2_indices(df, gid, moeda)
    if q2.empty or q2["indice_cartas"].isna().all():
        st.info("Sem dados suficientes.")
    else:
        fig = px.line(q2.melt("data", var_name="série", value_name="índice (base 100)"), x="data", y="índice (base 100)", color="série")
        fig.update_layout(legend_title=None, height=420)
        st.plotly_chart(fig, width="stretch")
        st.caption("Selados: média dos produtos com preço no 1º dia. Cartas: soma das cartas de raridade Double Rare em diante (um acabamento por carta). Último preço conhecido nos dias sem preço.")

with t3:
    st.subheader("Qual coleção da turma valorizou mais no período?")
    inicio = st.date_input("Início da janela (a partir do primeiro dia comum)", value=df["data"].min().date(), key="q3ini")
    col, ptax = q3_colecoes(df, moeda, inicio=inicio)
    if col.empty:
        st.info("Sem dados.")
    else:
        fig = px.line(col, x="data", y="indice", color="sigla", labels={"indice": "índice (base 100)"})
        for tr in fig.data:
            tr.update(line_width=4 if tr.name == sigla_sel else 1.5, opacity=1 if tr.name == sigla_sel else 0.7)
        if moeda == "BRL" and not ptax.empty:
            fig.add_scatter(x=ptax["data"], y=ptax["indice_ptax"], name="PTAX", line=dict(color="gray", dash="dash"))
        fig.update_layout(height=450, legend_title=None)
        st.plotly_chart(fig, width="stretch")
        fim = col.sort_values("data").groupby("sigla").tail(1).sort_values("indice", ascending=False)
        st.dataframe(fim[["sigla", "valor", "indice"]].rename(columns={"valor": f"valor ({moeda})", "indice": "índice final"}), hide_index=True)

with t4:
    st.subheader("Onde está concentrado o valor de cada coleção?")
    por_rar, n80 = q4_concentracao(df, moeda)
    if por_rar.empty:
        st.info("Sem dados.")
    else:
        fig = px.bar(por_rar, x="participacao", y="sigla", color="raridade", orientation="h", barmode="stack")
        fig.update_xaxes(tickformat=".0%", range=[0, 1])
        fig.update_layout(height=120 + 45 * por_rar["sigla"].nunique(), legend_title=None)
        st.plotly_chart(fig, width="stretch")
        n80["% das cartas"] = n80["cartas_80pct"] / n80["total_cartas"]
        st.dataframe(n80[["sigla", "cartas_80pct", "total_cartas", "% das cartas"]].style.format({"% das cartas": "{:.1%}"}), hide_index=True)
        st.caption("`cartas_80pct`: quantas cartas, das mais caras para as mais baratas, somam 80% do valor da coleção no último dia.")

with t5:
    st.subheader("Quais cartas da turma deram mais retorno para o risco assumido?")
    min5 = st.slider("Preço inicial mínimo (US$)", 1.0, 50.0, 5.0, 1.0, key="q5min")
    r5 = q5_risco_retorno(df, min_usd=min5, moeda=moeda)
    if r5.empty:
        st.info("Ainda não há observações suficientes (são necessários ao menos 4 dias por carta).")
    else:
        fig = px.scatter(r5, x="volatilidade", y="retorno", color="sigla", hover_name="nome",
                         hover_data={"raridade": True, "retorno_por_risco": ":.2f", "volatilidade": ":.2%", "retorno": ":.1%"})
        fig.update_yaxes(tickformat=".0%")
        fig.update_xaxes(tickformat=".1%", title="volatilidade (desvio-padrão dos retornos diários)")
        fig.update_layout(height=480, legend_title=None)
        st.plotly_chart(fig, width="stretch")
        top = r5.sort_values("retorno_por_risco", ascending=False).head(10)
        st.dataframe(
            top[["image_url", "nome", "sigla", "raridade", "retorno", "volatilidade", "retorno_por_risco"]],
            hide_index=True,
            column_config={
                "image_url": st.column_config.ImageColumn("carta", width="small"),
                "retorno": st.column_config.NumberColumn(format="%.1f%%", help="em fração × 100"),
                "volatilidade": st.column_config.NumberColumn(format="%.3f"),
                "retorno_por_risco": st.column_config.NumberColumn("retorno/risco", format="%.2f"),
            },
        )

with tc:
    st.subheader(f"Desafio: R$ 1.000 no primeiro dia — coleção {sigla_sel if gid == s.group_id else s.sigla}")
    try:
        sens = _carteira_gold("carteira_sensibilidade")
        comp = _carteira_gold("carteira_composicao")
    except Exception:  # noqa: BLE001
        sens = comp = None
        st.info("Rode `python -m pokelake portfolio` para gerar as carteiras.")

if sens is not None:
    with tc:
      com_taxa = st.toggle(f"Descontar taxa de venda de {s.taxa_venda:.0%}", value=True)
      curvas = sens[sens["taxa_venda"] == (s.taxa_venda if com_taxa else 0.0)].copy()
      curvas["carteira"] = curvas["carteira"].map(NOMES_CARTEIRA)
      fig = px.line(curvas, x="data", y="valor_brl", color="carteira", labels={"valor_brl": "valor de liquidação (R$)"})
      fig.add_hline(y=1000, line_dash="dot", line_color="gray")
      fig.update_layout(height=450, legend_title=None)
      st.plotly_chart(fig, width="stretch")
      m = metricas(sens[sens["taxa_venda"] == (s.taxa_venda if com_taxa else 0.0)])
      m["carteira"] = m["carteira"].astype(str).map(NOMES_CARTEIRA)
      st.dataframe(
          m.style.format({"valor_final_brl": "R$ {:,.2f}", "retorno_acumulado": "{:+.2%}", "excesso_sobre_cdi": "{:+.2%}", "perda_maxima": "{:.2%}"}),
          hide_index=True,
      )
      base = sens[sens["taxa_venda"] == s.taxa_venda].sort_values("data").groupby("carteira").tail(1).set_index("carteira")["retorno_acumulado"]
      zero = sens[sens["taxa_venda"] == 0.0].sort_values("data").groupby("carteira").tail(1).set_index("carteira")["retorno_acumulado"]
      sens_df = pd.DataFrame({"com taxa": base, "sem taxa": zero, "diferença": zero - base}).loc[["selado", "cesta_raras", "propria"]]
      st.markdown("**Sensibilidade à taxa de venda (retorno acumulado)**")
      st.dataframe(sens_df.style.format("{:+.2%}"))
      st.markdown("**O que foi comprado no primeiro dia** (unidades inteiras; a sobra fica em caixa e rende CDI)")
      st.dataframe(
          comp.assign(carteira=comp["carteira"].map(NOMES_CARTEIRA))[
              ["carteira", "nome", "acabamento", "unidades", "preco_compra_usd", "custo_brl", "caixa_inicial_brl"]
          ],
          hide_index=True,
      )
      st.caption("Valor de liquidação = unidades × preço × (1 − taxa) × PTAX de compra + caixa. Dias com preço carregado (último preço conhecido) aparecem na coluna `dias_preco_carregado`.")

with tp:
    st.subheader("Placar da turma")
    try:
        turma = _carteira_turma()
        pl = placar_turma(turma)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Coleções com carteira", pl["colecoes"])
        c2.metric("Selado ganhou do CDI", f"{pl.get('selado_ganhou_do_cdi', 0)} de {pl['colecoes']}")
        c3.metric("Cesta de raras ganhou do dólar", f"{pl.get('cesta_ganhou_do_dolar', 0)} de {pl['colecoes']}")
        gp = pl.get("menor_perda_maxima_group_id")
        c4.metric("Menor perda máxima", f"{df[df['group_id'] == gp]['sigla'].iloc[0] if gp in set(df['group_id']) else gp}", f"{pl.get('menor_perda_maxima', 0):.1%}")
        ret = pl["retornos"].copy()
        ret.index = [df[df["group_id"] == g]["sigla"].iloc[0] if g in set(df["group_id"]) else str(g) for g in ret.index]
        st.dataframe(ret[[c for c in CARTEIRAS if c in ret.columns]].rename(columns=NOMES_CARTEIRA).style.format("{:+.2%}"))
    except Exception as e:  # noqa: BLE001
        st.info(f"Ainda não há carteiras da turma em gold_turma/carteira/ ({e}).")

with tq:
    st.subheader("Qualidade dos dados e limites")
    st.markdown(
        f"- **{df['data'].nunique()} dias** com preço; **{df['product_id'].nunique()} produtos**; "
        f"{int(df['market_price'].isna().sum())} linhas com `market_price` nulo (nulo ≠ zero).\n"
        "- O `market_price` do TCGplayer vem de vendas recentes nos EUA, sem separar a condição da carta, "
        "sem frete, taxas nem preço do Brasil.\n"
        "- A PTAX é taxa de referência: cartão internacional paga outra cotação (spread + IOF).\n"
        "- Cerca de 7 semanas de série descrevem o período, não sustentam previsão nem recomendação de compra."
    )
    datas_all = pd.DataFrame({"data": pd.date_range(df["data"].min(), df["data"].max())})
    por_dia = df[df["group_id"] == gid].groupby("data").size().rename("linhas").reset_index()
    falt = datas_all.merge(por_dia, how="left", on="data")
    falt = falt[falt["linhas"].isna()]
    st.markdown(f"**Dias sem coleta para {sigla_sel}:** " + (", ".join(f"{d:%d/%m}" for d in falt["data"]) if not falt.empty else "nenhum"))
