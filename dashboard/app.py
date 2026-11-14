"""Dashboard: cartas Pokémon como ativo de coleção.

Rodar:  streamlit run dashboard/app.py
Lê o gold do próprio aluno (construído sobre a silver de toda a turma) e o placar em gold_turma/.
"""
from __future__ import annotations

import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from pokelake.analytics import (
    canonical,
    decompor,
    indice_cesta,
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

# ----------------------------------------------------------------------------- identidade visual
BG, S1, S2, BORDER = "#0B1020", "#141B31", "#1B2440", "#2A3558"
TXT, MUTED = "#E8ECF5", "#9AA6C7"
YELLOW, BLUE, GREEN, RED, ORANGE, PURPLE = "#FFCB05", "#5B7CFA", "#2ECC9A", "#FF6B6B", "#FF8A5B", "#B58CFF"
COLORWAY = [BLUE, ORANGE, GREEN, PURPLE, "#4FC3F7", "#F7B267", "#E56B9A", "#A3D977", "#7AD7F0", "#C9A0DC"]

NOMES_CARTEIRA = {
    "selado": "Selado (booster box)",
    "cesta_raras": "Cesta das 10 mais caras",
    "propria": "Carteira própria",
    "dolar": "Dólar parado",
    "cdi": "CDI",
}
COR_CARTEIRA = {
    "Selado (booster box)": BLUE,
    "Cesta das 10 mais caras": ORANGE,
    "Carteira própria": YELLOW,
    "Dólar parado": GREEN,
    "CDI": "#8D97B5",
}
# do comum (frio e apagado) ao raro (quente e brilhante)
COR_RARIDADE = {
    "Common": "#3A4670", "Uncommon": "#4A5A94", "Rare": "#5B7CFA", "Holo Rare": "#5B7CFA",
    "Double Rare": "#4FC3F7", "Ultra Rare": "#2ECC9A", "Illustration Rare": "#A3D977",
    "Special Illustration Rare": "#FFCB05", "Mega Attack Rare": "#FF8A5B", "Mega Hyper Rare": "#FF6B6B",
    "Hyper Rare": "#E56B9A", "Sem raridade": "#6B7595",
}
ORDEM_RARIDADE = list(COR_RARIDADE)

POKE = go.layout.Template()
POKE.layout = go.Layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TXT, family="Inter, system-ui, -apple-system, Segoe UI, sans-serif", size=13),
    colorway=COLORWAY,
    xaxis=dict(gridcolor="#222C4D", zerolinecolor="#2F3B63", linecolor=BORDER, tickcolor=BORDER, automargin=True, title=dict(standoff=12)),
    yaxis=dict(gridcolor="#222C4D", zerolinecolor="#2F3B63", linecolor=BORDER, tickcolor=BORDER, automargin=True, title=dict(standoff=12)),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.12, x=0, title_text=""),
    hoverlabel=dict(bgcolor=S2, bordercolor=BORDER, font_color=TXT),
    margin=dict(l=8, r=8, t=36, b=8),
)
pio.templates["poke"] = POKE
pio.templates.default = "poke"

CSS = """
<style>
:root{--bg:#0B1020;--s1:#141B31;--s2:#1B2440;--bd:#2A3558;--tx:#E8ECF5;--mu:#9AA6C7;--ac:#FFCB05;--bl:#5B7CFA;--up:#2ECC9A;--dn:#FF6B6B;}
.stApp{background:radial-gradient(1100px 520px at 8% -8%,#1a2350 0%,rgba(11,16,32,0) 62%),var(--bg);}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:1.4rem;max-width:1280px;}
[data-testid="stSidebar"]{background:var(--s1);border-right:1px solid var(--bd);}
h2,h3{letter-spacing:-.01em;}

.hero{background:linear-gradient(115deg,#1c2a6e 0%,#3b4cca 48%,#7b3fe4 100%);border-radius:22px;padding:26px 30px;margin:0 0 18px 0;position:relative;overflow:hidden;box-shadow:0 12px 40px rgba(59,76,202,.28);}
.hero:after{content:"";position:absolute;right:-60px;top:-60px;width:260px;height:260px;border-radius:50%;background:radial-gradient(circle,rgba(255,203,5,.55) 0%,rgba(255,203,5,0) 68%);}
.hero-t{font-size:2.05rem;font-weight:800;color:#fff;letter-spacing:-.02em;line-height:1.15;}
.hero-s{color:#D5DBFF;margin-top:6px;font-size:1.0rem;}
.chips{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px;position:relative;z-index:1;}
.chip{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.22);color:#fff;border-radius:999px;padding:4px 12px;font-size:.82rem;font-weight:600;backdrop-filter:blur(4px);}

.kpi{background:var(--s1);border:1px solid var(--bd);border-radius:16px;padding:14px 18px;height:100%;}
.kpi-l{color:var(--mu);font-size:.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;}
.kpi-v{font-size:1.65rem;font-weight:800;color:var(--tx);margin-top:2px;letter-spacing:-.01em;}
.kpi-h{color:var(--mu);font-size:.8rem;margin-top:2px;}

.pill{display:inline-block;border-radius:999px;padding:2px 10px;font-weight:700;font-size:.82rem;}
.pill.big{font-size:1.0rem;padding:3px 12px;}
.pill.up{background:rgba(46,204,154,.16);color:var(--up);}
.pill.dn{background:rgba(255,107,107,.16);color:var(--dn);}
.pill.nn{background:rgba(154,166,199,.16);color:var(--mu);}

.sec{display:flex;align-items:center;gap:10px;margin:22px 0 10px 0;font-size:1.15rem;font-weight:700;color:var(--tx);}
.sec .bar{width:5px;height:22px;border-radius:3px;background:var(--ac);}
.sec.dn .bar{background:var(--dn);} .sec.up .bar{background:var(--up);}
.q{color:var(--mu);margin:-4px 0 14px 0;font-size:.95rem;}

.cardx{background:var(--s1);border:1px solid var(--bd);border-radius:16px;padding:10px;transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease;height:100%;}
.cardx:hover{transform:translateY(-4px);border-color:var(--ac);box-shadow:0 10px 26px rgba(0,0,0,.45);}
.imgwrap{position:relative;border-radius:12px;overflow:hidden;background:var(--s2);aspect-ratio:245/342;}
.imgwrap img{width:100%;height:100%;object-fit:cover;display:block;}
.rank{position:absolute;left:8px;top:8px;background:var(--ac);color:#10152B;font-weight:800;font-size:.8rem;border-radius:999px;padding:2px 9px;z-index:2;box-shadow:0 2px 8px rgba(0,0,0,.4);}
.cname{display:block;margin-top:9px;color:var(--tx)!important;font-weight:700;font-size:.92rem;line-height:1.25;text-decoration:none;}
.cname:hover{color:var(--ac)!important;}
.meta{color:var(--mu);font-size:.76rem;margin-top:2px;}
.prices{color:var(--mu);font-size:.82rem;margin-top:8px;}
.prices b{color:var(--tx);}
.var{margin-top:6px;}
.split{display:flex;flex-wrap:wrap;gap:4px 10px;margin-top:8px;color:var(--mu);font-size:.72rem;border-top:1px dashed var(--bd);padding-top:7px;}

.show{background:linear-gradient(180deg,var(--s2),var(--s1));border:1px solid var(--bd);border-radius:16px;padding:10px;text-align:center;height:100%;}
.show img{width:100%;border-radius:10px;display:block;aspect-ratio:245/342;object-fit:cover;background:var(--s1);}
.show .n{font-weight:700;font-size:.85rem;margin-top:8px;color:var(--tx);line-height:1.2;}
.show .p{font-weight:800;color:var(--ac);margin-top:3px;}

.cart{background:var(--s1);border:1px solid var(--bd);border-radius:16px;padding:14px 16px;border-top:4px solid var(--c,#5B7CFA);height:100%;}
.cart .t{color:var(--mu);font-size:.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;}
.cart .v{font-size:1.45rem;font-weight:800;margin:4px 0 6px 0;}

.stTabs [data-baseweb="tab-list"]{gap:4px;border-bottom:1px solid var(--bd);flex-wrap:wrap;}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:10px 10px 0 0;padding:10px 14px;color:var(--mu);font-weight:600;}
.stTabs [aria-selected="true"]{color:var(--ac);background:rgba(255,203,5,.07);}
[data-testid="stDataFrame"]{border:1px solid var(--bd);border-radius:12px;overflow:hidden;}
.foot{color:var(--mu);font-size:.78rem;margin-top:26px;text-align:center;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------- dados
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


# ----------------------------------------------------------------------------- formatação e componentes
def _h(s: str) -> str:
    """HTML em uma linha só: o Markdown trata linhas indentadas como bloco de código."""
    return " ".join(x.strip() for x in s.strip().splitlines())


def num(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl(x: float) -> str:
    return f"R$ {num(x)}"


def money(x: float, moeda: str) -> str:
    return brl(x) if moeda == "BRL" else f"US$ {num(x)}"


def spct(x: float) -> str:
    return f"{x * 100:+.1f}%".replace(".", ",")


def pill(x, big: bool = False) -> str:
    if x is None or pd.isna(x):
        return '<span class="pill nn">—</span>'
    cls, arrow = ("up", "▲") if x > 0 else ("dn", "▼") if x < 0 else ("nn", "■")
    txt = f"{abs(x) * 100:.1f}%".replace(".", ",")
    return f'<span class="pill {cls}{" big" if big else ""}">{arrow} {txt}</span>'


def kpi(label: str, value: str, hint: str = "") -> str:
    h = f'<div class="kpi-h">{hint}</div>' if hint else ""
    return _h(f'<div class="kpi"><div class="kpi-l">{html.escape(label)}</div><div class="kpi-v">{value}</div>{h}</div>')


def section(titulo: str, tom: str = "") -> None:
    st.markdown(f'<div class="sec {tom}"><span class="bar"></span>{titulo}</div>', unsafe_allow_html=True)


def pergunta(txt: str) -> None:
    st.markdown(f'<div class="q">{txt}</div>', unsafe_allow_html=True)


def card_html(r, moeda: str, rank: int) -> str:
    simb = "R$" if moeda == "BRL" else "US$"
    ini, fim = (r["brl_ini"], r["brl_fim"]) if moeda == "BRL" else (r["usd_ini"], r["usd_fim"])
    var = r["var_brl"] if moeda == "BRL" else r["efeito_carta"]
    nome = html.escape(str(r["nome"]))
    meta = html.escape(f"{r['acabamento']} · {r['raridade'] or '—'}")
    url = html.escape(str(r["url"] or "#"), quote=True)
    img = html.escape(str(r["image_url"] or ""), quote=True)
    split = (
        f'<div class="split"><span>carta {spct(r["efeito_carta"])}</span><span>câmbio {spct(r["efeito_cambio"])}</span>'
        f'<span>cruzado {spct(r["efeito_cruzado"])}</span></div>'
        if moeda == "BRL"
        else ""
    )
    return _h(
        f'<div class="cardx"><div class="imgwrap"><span class="rank">#{rank}</span>'
        f'<img src="{img}" loading="lazy" alt="{nome}"/></div>'
        f'<a class="cname" href="{url}" target="_blank" rel="noopener">{nome}</a><div class="meta">{meta}</div>'
        f'<div class="prices">{simb} {num(ini)} → <b>{simb} {num(fim)}</b></div>'
        f'<div class="var">{pill(var, True)}</div>{split}</div>'
    )


def grade_cartas(df: pd.DataFrame, moeda: str) -> None:
    cols = st.columns(5)
    for i, (_, r) in enumerate(df.iterrows()):
        cols[i % 5].markdown(card_html(r, moeda, i + 1), unsafe_allow_html=True)


def vitrine(g: pd.DataFrame, moeda: str, n: int = 5) -> None:
    col = "market_price_brl" if moeda == "BRL" else "market_price"
    c = canonical(g).dropna(subset=[col]).sort_values("data").groupby("product_id").tail(1).nlargest(n, col)
    cols = st.columns(n)
    for i, (_, r) in enumerate(c.iterrows()):
        nome = html.escape(str(r["nome"]))
        url = html.escape(str(r["url"] or "#"), quote=True)
        img = html.escape(str(r["image_url"] or ""), quote=True)
        cols[i].markdown(
            _h(
                f'<a href="{url}" target="_blank" rel="noopener" style="text-decoration:none">'
                f'<div class="show"><img src="{img}" loading="lazy" alt="{nome}"/>'
                f'<div class="n">{nome}</div><div class="p">{money(r[col], moeda)}</div></div></a>'
            ),
            unsafe_allow_html=True,
        )


def plot(fig: go.Figure, height: int = 430) -> None:
    fig.update_layout(height=height)
    st.plotly_chart(fig, width="stretch", theme=None)


# ----------------------------------------------------------------------------- carga
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

with st.sidebar:
    st.markdown("### 🎛️ Filtros")
    moeda = st.radio("Moeda", ["BRL", "USD"], horizontal=True, help="Os filtros de preço mínimo são sempre em US$.")
    colecoes = df[["group_id", "sigla", "colecao"]].drop_duplicates().sort_values("sigla")
    opcoes = dict(zip(colecoes["sigla"], colecoes["group_id"]))
    padrao = list(opcoes).index(s.sigla) if s.sigla in opcoes else 0
    sigla_sel = st.selectbox("Minha coleção", list(opcoes), index=padrao)
    gid = int(opcoes[sigla_sel])
    st.caption("Os filtros de preço mínimo ficam em US$, para a lista não mudar quando o câmbio muda.")

g = df[df["group_id"] == gid]
col_preco = "market_price_brl" if moeda == "BRL" else "market_price"
datas = df["data"]
ult = cambio.dropna(subset=["cotacao_venda"]).iloc[-1]
nome_colecao = g["colecao"].iloc[0]

# ----------------------------------------------------------------------------- topo
st.markdown(
    _h(
        f'<div class="hero"><div class="hero-t">🃏 Cartas Pokémon como ativo de coleção</div>'
        f'<div class="hero-s">{html.escape(nome_colecao)} · preços do TCGplayer convertidos pela PTAX do dia</div>'
        f'<div class="chips"><span class="chip">📅 {datas.min():%d/%m} a {datas.max():%d/%m/%Y}</span>'
        f'<span class="chip">🗓️ {datas.nunique()} dias com preço</span>'
        f'<span class="chip">💵 PTAX venda {ult["cotacao_venda"]:.4f}</span>'
        f'<span class="chip">💱 exibindo em {moeda}</span></div></div>'
    ),
    unsafe_allow_html=True,
)
if "demo" in str(s.local_root).lower() or df["nome"].str.startswith("DEMO").any():
    st.warning("Dados SINTÉTICOS de demonstração. Não use para decidir nada.")

serie_valor = indice_cesta(canonical(g), col_preco, agg="sum")
n_cartas = canonical(g)["product_id"].nunique()
n_selados = g[(g["tipo_produto"] == "selado") & (~g["is_code_card"].astype(bool))]["product_id"].nunique()
k1, k2, k3, k4 = st.columns(4)
if len(serie_valor):
    var_total = serie_valor.iloc[-1] / serie_valor.iloc[0] - 1 if len(serie_valor) > 1 else None
    k1.markdown(
        kpi("Valor de um exemplar de cada carta", money(serie_valor.iloc[-1], moeda), "último dia coletado"),
        unsafe_allow_html=True,
    )
    k2.markdown(
        kpi("Variação no período", pill(var_total, True) if var_total is not None else "—", f"desde {serie_valor.index[0]:%d/%m}"),
        unsafe_allow_html=True,
    )
k3.markdown(kpi("Cartas acompanhadas", f"{n_cartas:,}".replace(",", "."), "sem Code Cards"), unsafe_allow_html=True)
k4.markdown(kpi("Produtos selados", f"{n_selados:,}".replace(",", "."), "boxes, ETB, bundles, blisters"), unsafe_allow_html=True)

section("As cartas mais valiosas da coleção")
vitrine(g, moeda)

st.write("")
t1, t2, t3, t4, t5, tc, tp, tq = st.tabs(
    ["1 · Valorização", "2 · Selado × cartas", "3 · Coleções", "4 · Concentração", "5 · Risco × retorno",
     "💰 Carteira R$ 1.000", "🏆 Placar da turma", "🔎 Qualidade dos dados"]
)

# ----------------------------------------------------------------------------- 1
with t1:
    pergunta("Quais cartas da minha coleção mais valorizaram e mais desvalorizaram desde o início da coleta?")
    min_usd = st.slider("Preço inicial mínimo (US$)", 0.0, 20.0, 1.0, 0.5, key="q1min")
    ganhos, perdas = q1_variacao(df, gid, min_usd=min_usd, moeda=moeda)
    if ganhos.empty:
        st.info("Ainda não há duas observações por carta para calcular variação.")
    else:
        section("📈 Maiores valorizações", "up")
        grade_cartas(ganhos, moeda)
        section("📉 Maiores desvalorizações", "dn")
        grade_cartas(perdas, moeda)
        st.caption(
            "Variação em R$ = (1 + carta) × (1 + câmbio) − 1. Considera só cartas com preço inicial ≥ US$ "
            f"{min_usd:.2f}; Code Cards ficam de fora. Período: {ganhos['data_ini'].min():%d/%m} a {ganhos['data_fim'].max():%d/%m}."
        )
        ex = ganhos.iloc[0]
        chk = decompor(ex["usd_ini"], ex["usd_fim"], ex["ptax_ini"], ex["ptax_fim"])
        st.caption(
            f"Conferência: {ex['nome']} → {spct(chk['var_brl'])} = carta {spct(chk['efeito_carta'])} "
            f"+ câmbio {spct(chk['efeito_cambio'])} + cruzado {spct(chk['efeito_cruzado'])}."
        )

# ----------------------------------------------------------------------------- 2
with t2:
    pergunta("Na minha coleção, o produto selado guardou valor melhor que as cartas avulsas?")
    q2 = q2_indices(df, gid, moeda)
    if q2.empty or q2["indice_cartas"].isna().all():
        st.info("Sem dados suficientes.")
    else:
        q2 = q2.rename(columns={"indice_selados": "Selados (média)", "indice_cartas": "Cartas Double Rare+ (soma)"})
        fig = px.line(
            q2.melt("data", var_name="série", value_name="índice (base 100)"),
            x="data", y="índice (base 100)", color="série", markers=True,
            color_discrete_map={"Selados (média)": BLUE, "Cartas Double Rare+ (soma)": YELLOW},
        )
        fig.update_traces(line_width=3.5)
        fig.add_hline(y=100, line_dash="dot", line_color="#55618a")
        plot(fig, 420)
        ult2 = q2.iloc[-1]
        a, b = st.columns(2)
        a.markdown(kpi("Selados", pill(ult2["Selados (média)"] / 100 - 1, True), "índice base 100 no 1º dia"), unsafe_allow_html=True)
        b.markdown(kpi("Cartas Double Rare+", pill(ult2["Cartas Double Rare+ (soma)"] / 100 - 1, True), "índice base 100 no 1º dia"), unsafe_allow_html=True)
        st.caption("Selados: média dos produtos com preço no 1º dia. Cartas: soma das cartas de raridade Double Rare em diante (um acabamento por carta). Último preço conhecido nos dias sem preço.")

# ----------------------------------------------------------------------------- 3
with t3:
    pergunta("Qual coleção da turma valorizou mais no período?")
    inicio = st.date_input("Início da janela (a partir do primeiro dia comum)", value=df["data"].min().date(), key="q3ini")
    col, ptax = q3_colecoes(df, moeda, inicio=inicio)
    if col.empty:
        st.info("Sem dados.")
    else:
        siglas = sorted(col["sigla"].unique())
        cmap = {sg: COLORWAY[i % len(COLORWAY)] for i, sg in enumerate(s for s in siglas if s != sigla_sel)}
        cmap[sigla_sel] = YELLOW
        fig = px.line(col, x="data", y="indice", color="sigla", labels={"indice": "índice (base 100)"}, color_discrete_map=cmap)
        for tr in fig.data:
            propria = tr.name == sigla_sel
            tr.update(line_width=4.5 if propria else 2, opacity=1 if propria else 0.75)
        if moeda == "BRL" and not ptax.empty:
            fig.add_scatter(x=ptax["data"], y=ptax["indice_ptax"], name="PTAX", line=dict(color="#8D97B5", dash="dash", width=2))
        fig.add_hline(y=100, line_dash="dot", line_color="#55618a")
        plot(fig, 450)
        fim = col.sort_values("data").groupby("sigla").tail(1).sort_values("indice", ascending=False)
        st.dataframe(
            fim[["sigla", "valor", "indice"]].rename(columns={"valor": f"valor ({moeda})", "indice": "índice final"}),
            hide_index=True,
            column_config={f"valor ({moeda})": st.column_config.NumberColumn(format="%.2f"),
                           "índice final": st.column_config.ProgressColumn(format="%.1f", min_value=0, max_value=float(max(120, fim["indice"].max())))},
        )

# ----------------------------------------------------------------------------- 4
with t4:
    pergunta("Onde está concentrado o valor de cada coleção?")
    por_rar, n80 = q4_concentracao(df, moeda)
    if por_rar.empty:
        st.info("Sem dados.")
    else:
        ordem = [r for r in ORDEM_RARIDADE if r in set(por_rar["raridade"])] + sorted(set(por_rar["raridade"]) - set(ORDEM_RARIDADE))
        fig = px.bar(por_rar, x="participacao", y="sigla", color="raridade", orientation="h", barmode="stack",
                     category_orders={"raridade": ordem}, color_discrete_map=COR_RARIDADE)
        fig.update_xaxes(tickformat=".0%", range=[0, 1])
        fig.update_traces(marker_line_color=BG, marker_line_width=1.5)
        plot(fig, 130 + 46 * por_rar["sigla"].nunique())
        n80["% das cartas"] = n80["cartas_80pct"] / n80["total_cartas"]
        st.dataframe(
            n80[["sigla", "cartas_80pct", "total_cartas", "% das cartas"]],
            hide_index=True,
            column_config={"% das cartas": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=1)},
        )
        st.caption("`cartas_80pct`: quantas cartas, das mais caras para as mais baratas, somam 80% do valor da coleção no último dia.")

# ----------------------------------------------------------------------------- 5
with t5:
    pergunta("Quais cartas da turma deram mais retorno para o risco assumido?")
    min5 = st.slider("Preço inicial mínimo (US$)", 1.0, 50.0, 5.0, 1.0, key="q5min")
    r5 = q5_risco_retorno(df, min_usd=min5, moeda=moeda)
    if r5.empty:
        st.info("Ainda não há observações suficientes (são necessários ao menos 4 dias por carta).")
    else:
        fig = px.scatter(
            r5, x="volatilidade", y="retorno", color="sigla", size="preco_ini_usd", size_max=26, hover_name="nome",
            hover_data={"raridade": True, "retorno_por_risco": ":.2f", "volatilidade": ":.2%", "retorno": ":.1%", "preco_ini_usd": ":.2f"},
        )
        fig.update_traces(marker=dict(opacity=0.8, line=dict(width=1, color=BG)))
        fig.add_hline(y=0, line_dash="dot", line_color="#55618a")
        fig.update_yaxes(tickformat=".0%", title="retorno no período")
        fig.update_xaxes(tickformat=".1%", title="volatilidade (desvio-padrão dos retornos diários)")
        plot(fig, 480)
        section("As 10 melhores relações retorno/risco")
        top = r5.sort_values("retorno_por_risco", ascending=False).head(10)
        st.dataframe(
            top[["image_url", "nome", "sigla", "raridade", "retorno", "volatilidade", "retorno_por_risco", "url"]],
            hide_index=True,
            column_config={
                "image_url": st.column_config.ImageColumn("carta", width="small"),
                "retorno": st.column_config.NumberColumn(format="percent"),
                "volatilidade": st.column_config.NumberColumn(format="percent"),
                "retorno_por_risco": st.column_config.NumberColumn("retorno/risco", format="%.2f"),
                "url": st.column_config.LinkColumn("TCGplayer", display_text="abrir"),
            },
        )

# ----------------------------------------------------------------------------- carteira
with tc:
    pergunta(f"Desafio: R$ 1.000 no primeiro dia de coleta — coleção {s.sigla}. Cartas, selado, dólar ou CDI?")
    try:
        sens = _carteira_gold("carteira_sensibilidade")
        comp = _carteira_gold("carteira_composicao")
    except Exception:  # noqa: BLE001
        sens = comp = None
        st.info("Rode `python -m pokelake portfolio` para gerar as carteiras.")
    if sens is not None:
        com_taxa = st.toggle(f"Descontar taxa de venda de {s.taxa_venda:.0%}", value=True)
        taxa = s.taxa_venda if com_taxa else 0.0
        cur = sens[sens["taxa_venda"] == taxa]
        m = metricas(cur)
        cols = st.columns(5)
        for i, (_, r) in enumerate(m.iterrows()):
            nome = NOMES_CARTEIRA[str(r["carteira"])]
            cols[i].markdown(
                _h(
                    f'<div class="cart" style="--c:{COR_CARTEIRA[nome]}"><div class="t">{html.escape(nome)}</div>'
                    f'<div class="v">{brl(r["valor_final_brl"])}</div>{pill(r["retorno_acumulado"], True)}</div>'
                ),
                unsafe_allow_html=True,
            )
        st.write("")
        curvas = cur.copy()
        curvas["carteira"] = curvas["carteira"].map(NOMES_CARTEIRA)
        fig = px.line(curvas, x="data", y="valor_brl", color="carteira", labels={"valor_brl": "valor de liquidação (R$)"},
                      color_discrete_map=COR_CARTEIRA)
        fig.update_traces(line_width=3)
        for tr in fig.data:
            if tr.name == "CDI":
                tr.update(line_dash="dash")
        fig.add_hline(y=1000, line_dash="dot", line_color="#55618a", annotation_text="R$ 1.000", annotation_font_color=MUTED)
        plot(fig, 430)
        mm = m.copy()
        mm["carteira"] = mm["carteira"].astype(str).map(NOMES_CARTEIRA)
        st.dataframe(
            mm.style.format({"valor_final_brl": "R$ {:,.2f}", "retorno_acumulado": "{:+.2%}", "excesso_sobre_cdi": "{:+.2%}", "perda_maxima": "{:.2%}"}),
            hide_index=True,
        )
        base = sens[sens["taxa_venda"] == s.taxa_venda].sort_values("data").groupby("carteira").tail(1).set_index("carteira")["retorno_acumulado"]
        zero = sens[sens["taxa_venda"] == 0.0].sort_values("data").groupby("carteira").tail(1).set_index("carteira")["retorno_acumulado"]
        sens_df = pd.DataFrame({"com taxa": base, "sem taxa": zero, "diferença": zero - base}).loc[["selado", "cesta_raras", "propria"]]
        sens_df.index = [NOMES_CARTEIRA[i] for i in sens_df.index]
        section("Sensibilidade à taxa de venda (retorno acumulado)")
        st.dataframe(sens_df.style.format("{:+.2%}"))
        section("O que foi comprado no primeiro dia")
        st.caption("Unidades inteiras; a sobra fica em caixa e rende CDI.")
        st.dataframe(
            comp.assign(carteira=comp["carteira"].map(NOMES_CARTEIRA))[
                ["carteira", "nome", "acabamento", "unidades", "preco_compra_usd", "custo_brl", "caixa_inicial_brl"]
            ],
            hide_index=True,
        )
        st.caption("Valor de liquidação = unidades × preço × (1 − taxa) × PTAX de compra + caixa. Dias com preço carregado (último preço conhecido) aparecem na coluna `dias_preco_carregado`.")

# ----------------------------------------------------------------------------- placar
with tp:
    pergunta("Como as carteiras de toda a turma se comportaram?")
    try:
        turma = _carteira_turma()
        pl = placar_turma(turma)
        c1, c2, c3, c4 = st.columns(4)
        gp = pl.get("menor_perda_maxima_group_id")
        sg_menor = df[df["group_id"] == gp]["sigla"].iloc[0] if gp in set(df["group_id"]) else str(gp)
        c1.markdown(kpi("Coleções com carteira", str(pl["colecoes"])), unsafe_allow_html=True)
        c2.markdown(kpi("Selado ganhou do CDI", f"{pl.get('selado_ganhou_do_cdi', 0)} de {pl['colecoes']}"), unsafe_allow_html=True)
        c3.markdown(kpi("Cesta ganhou do dólar", f"{pl.get('cesta_ganhou_do_dolar', 0)} de {pl['colecoes']}"), unsafe_allow_html=True)
        c4.markdown(kpi("Menor perda máxima", sg_menor, pill(pl.get("menor_perda_maxima", 0.0))), unsafe_allow_html=True)
        st.write("")
        ret = pl["retornos"].copy()
        ret.index = [df[df["group_id"] == x]["sigla"].iloc[0] if x in set(df["group_id"]) else str(x) for x in ret.index]
        st.dataframe(ret[[c for c in CARTEIRAS if c in ret.columns]].rename(columns=NOMES_CARTEIRA).style.format("{:+.2%}"))
    except Exception as e:  # noqa: BLE001
        st.info(f"Ainda não há carteiras da turma em gold_turma/carteira/ ({e}).")

# ----------------------------------------------------------------------------- qualidade
with tq:
    pergunta("Quanto dá para confiar nos números?")
    q1c, q2c, q3c = st.columns(3)
    q1c.markdown(kpi("Dias com preço", str(df["data"].nunique())), unsafe_allow_html=True)
    q2c.markdown(kpi("Produtos", f"{df['product_id'].nunique():,}".replace(",", ".")), unsafe_allow_html=True)
    q3c.markdown(kpi("Preços nulos", f"{int(df['market_price'].isna().sum()):,}".replace(",", "."), "nulo ≠ zero"), unsafe_allow_html=True)
    st.write("")
    st.markdown(
        "- O `market_price` do TCGplayer vem de vendas recentes nos EUA, sem separar a condição da carta, "
        "sem frete, taxas nem preço do Brasil.\n"
        "- A PTAX é taxa de referência: cartão internacional paga outra cotação (spread + IOF).\n"
        "- Poucas semanas de série descrevem o período; não sustentam previsão nem recomendação de compra."
    )
    datas_all = pd.DataFrame({"data": pd.date_range(df["data"].min(), df["data"].max())})
    por_dia = df[df["group_id"] == gid].groupby("data").size().rename("linhas").reset_index()
    falt = datas_all.merge(por_dia, how="left", on="data")
    falt = falt[falt["linhas"].isna()]
    st.markdown(f"**Dias sem coleta para {sigla_sel}:** " + (", ".join(f"{d:%d/%m}" for d in falt["data"]) if not falt.empty else "nenhum"))

st.markdown('<div class="foot">Dados: TCGplayer via TCGCSV · PTAX e CDI: Banco Central. Evidência sobre o período, não recomendação de compra.</div>', unsafe_allow_html=True)
