"""Dados SINTÉTICOS no formato do TCGCSV, só para testar o pipeline e o dashboard localmente.

ATENÇÃO: nunca grave isto no data lake da turma. Dado inventado invalida as perguntas que o usam.
O comando `demo` recusa rodar com POKELAKE_BACKEND=s3.
"""
from __future__ import annotations

import json
from urllib.parse import quote
from datetime import date, timedelta

import numpy as np

from pokelake.config import Settings
from pokelake.keys import raw_key
from pokelake.storage import BaseLake

# Imagem de demonstração embutida (SVG): funciona sem internet e nunca parece uma carta real.
DEMO_IMG = "data:image/svg+xml;utf8," + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" width="245" height="342" viewBox="0 0 245 342">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3B4CCA"/>'
    '<stop offset="1" stop-color="#7B3FE4"/></linearGradient></defs><rect width="245" height="342" rx="14" fill="url(#g)"/>'
    '<circle cx="122" cy="150" r="52" fill="#FFCB05" opacity=".9"/><text x="122" y="290" font-size="26" font-family="sans-serif" '
    'font-weight="700" fill="#fff" text-anchor="middle">DEMO</text></svg>'
)

RARIDADES = ["Common"] * 12 + ["Uncommon"] * 10 + ["Rare"] * 6 + ["Double Rare"] * 5 + [
    "Illustration Rare"] * 3 + ["Ultra Rare"] * 2 + ["Special Illustration Rare"] * 3 + ["Hyper Rare"] * 1


def _dias(fim: date, n: int) -> list[date]:
    return [fim - timedelta(days=i) for i in range(n - 1, -1, -1)]


def _gera_colecao(lake: BaseLake, gid: int, dias: list[date], seed: int) -> None:
    rng = np.random.default_rng(seed)
    produtos, base = [], {}
    pid0 = gid * 1000
    for i, rar in enumerate(RARIDADES):
        pid = pid0 + i
        mult = {"Common": 0.15, "Uncommon": 0.3, "Rare": 0.8, "Double Rare": 2, "Illustration Rare": 12,
                "Ultra Rare": 8, "Special Illustration Rare": 60, "Hyper Rare": 25}[rar]
        base[(pid, "Holofoil" if rar not in ("Common", "Uncommon") else "Normal")] = mult * rng.uniform(0.6, 1.6)
        produtos.append({"productId": pid, "name": f"DEMO Carta {i:03d}", "imageUrl": DEMO_IMG,
                         "url": "https://example.com/demo", "extendedData": [
                             {"name": "Rarity", "value": rar}, {"name": "Number", "value": f"{i + 1:03d}/100"}]})
    for j, nome in enumerate(["DEMO Booster Box", "DEMO Booster Box Case", "DEMO Elite Trainer Box", "DEMO Booster Bundle"]):
        pid = pid0 + 500 + j
        base[(pid, "Normal")] = [130, 780, 55, 28][j] * rng.uniform(0.9, 1.1)
        produtos.append({"productId": pid, "name": nome, "imageUrl": DEMO_IMG,
                         "url": "https://example.com/demo", "extendedData": []})
    prod_body = json.dumps({"success": True, "errors": [], "results": produtos}).encode()
    preco = dict(base)
    for d in dias:
        prices = []
        for (pid, acab), v in preco.items():
            preco[(pid, acab)] = max(0.05, v * (1 + rng.normal(0.002, 0.025)))
            mp = None if rng.random() < 0.02 else round(preco[(pid, acab)], 2)  # nulo ocasional
            prices.append({"productId": pid, "lowPrice": round(preco[(pid, acab)] * 0.9, 2), "midPrice": round(preco[(pid, acab)], 2),
                           "highPrice": round(preco[(pid, acab)] * 1.4, 2), "marketPrice": mp, "directLowPrice": None, "subTypeName": acab})
        lake.put_if_absent(raw_key("tcgplayer", gid, d, "products.json"), prod_body)
        lake.put_if_absent(raw_key("tcgplayer", gid, d, "prices.json"), json.dumps({"success": True, "errors": [], "results": prices}).encode())


def seed_demo(lake: BaseLake, s: Settings, fim: date | None = None, n_dias: int = 30) -> list[int]:
    if lake.kind != "local":
        raise RuntimeError("seed_demo só roda com backend local: nunca grave dado sintético no lake da turma.")
    fim = fim or date.today()
    dias = _dias(fim, n_dias)
    grupos = [s.group_id] + [g for g in (24325, 23651) if g != s.group_id]
    rng = np.random.default_rng(7)
    ptax = 5.0
    ptax_por_dia: dict[date, tuple[float, float]] = {}
    for d in _dias(fim, n_dias + 12):
        ptax *= 1 + rng.normal(0, 0.004)
        if d.weekday() < 5:
            ptax_por_dia[d] = (round(ptax - 0.0003, 4), round(ptax + 0.0003, 4))
    for gid in grupos:
        for i, d in enumerate(_dias(fim, n_dias + 5)):
            k = raw_key("bcb_ptax", gid, d, "cotacao.json")
            valor = []
            if d in ptax_por_dia:
                c, v = ptax_por_dia[d]
                valor = [{"cotacaoCompra": c, "cotacaoVenda": v, "dataHoraCotacao": f"{d} 13:09:02.713", "tipoBoletim": "Fechamento"}]
            lake.put_if_absent(k, json.dumps({"value": valor}).encode())
        for d in dias:
            janela = [{"data": f"{x:%d/%m/%Y}", "valor": "0.050788"} for x in _dias(d - timedelta(days=1), 10) if x.weekday() < 5]
            lake.put_if_absent(raw_key("bcb_cdi", gid, d, "cdi.json"), json.dumps(janela).encode())
        _gera_colecao(lake, gid, dias, seed=gid)
    return grupos
