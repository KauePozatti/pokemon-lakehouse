"""Coleta diária: TCGplayer (via TCGCSV), PTAX e CDI do Banco Central -> camada bruta.

Regras:
- O bruto é imutável: nenhuma chave de `raw/` é sobrescrita (`put_if_absent`).
- Rodar duas vezes no mesmo dia não duplica nada (idempotência).
- O corpo gravado é a resposta original, sem transformação.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pokelake.config import CATEGORY_ID, Settings
from pokelake.http import Fetcher
from pokelake.keys import raw_key
from pokelake.storage import BaseLake

log = logging.getLogger("pokelake.collect")

TCG_BASE = f"https://tcgcsv.com/tcgplayer/{CATEGORY_ID}"
TCG_LAST_UPDATED = "https://tcgcsv.com/last-updated.txt"
PTAX_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)"
)
CDI_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados"
BRT = ZoneInfo("America/Sao_Paulo")


class DadoDefasadoError(RuntimeError):
    """O TCGCSV ainda não publicou a atualização do dia (ela sai por volta de 20h UTC)."""


def hoje_brt() -> date:
    return datetime.now(BRT).date()


def _verifica_frescor(fetcher: Fetcher, hoje: date) -> None:
    """Evita gravar o preço de ontem na chave de hoje. Falha aberta: se não der para
    ler/interpretar o carimbo, a coleta segue (o erro vira apenas um aviso no log)."""
    try:
        txt = fetcher.get(TCG_LAST_UPDATED).decode().strip()
        m = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", txt)
        if not m:
            log.warning("last-updated.txt em formato inesperado: %r", txt[:60])
            return
        ts = datetime.fromisoformat(m.group(0)).replace(tzinfo=timezone.utc).astimezone(BRT)
    except Exception as e:  # noqa: BLE001
        log.warning("Não foi possível verificar o frescor do TCGCSV: %s", e)
        return
    if ts.date() < hoje:
        raise DadoDefasadoError(
            f"TCGCSV atualizado por último em {ts:%d/%m/%Y %H:%M} (BRT); ainda não há dado de {hoje:%d/%m/%Y}. "
            "Rode depois das 17h (BRT) ou use --allow-stale por sua conta e risco."
        )


def _valida_tcg(raw: bytes, nome: str) -> None:
    j = json.loads(raw)
    if not isinstance(j.get("results"), list) or not j["results"]:
        raise ValueError(f"Resposta de {nome} sem 'results' — não vou gravar no bruto")


def collect(
    lake: BaseLake,
    s: Settings,
    fetcher: Fetcher | None = None,
    hoje: date | None = None,
    allow_stale: bool = False,
    ptax_lookback: int = 5,
    cdi_window: int = 10,
) -> dict:
    """Coleta o dia. Devolve um relatório {fonte: {chave: 'gravado' | 'ja_existia'}}."""
    fetcher = fetcher or Fetcher(s.user_agent, s.pause_s)
    hoje = hoje or hoje_brt()
    gid = s.group_id
    rel: dict[str, dict[str, str]] = {"tcgplayer": {}, "bcb_ptax": {}, "bcb_cdi": {}}

    # --- TCGplayer (3 chamadas por dia: last-updated + products + prices) ---
    alvos = {"products.json": f"{TCG_BASE}/{gid}/products", "prices.json": f"{TCG_BASE}/{gid}/prices"}
    faltando = {n: u for n, u in alvos.items() if not lake.exists(raw_key("tcgplayer", gid, hoje, n))}
    if faltando and not allow_stale:
        _verifica_frescor(fetcher, hoje)
    for nome, url in alvos.items():
        k = raw_key("tcgplayer", gid, hoje, nome)
        if nome not in faltando:
            rel["tcgplayer"][k] = "ja_existia"
            continue
        body = fetcher.get(url)
        _valida_tcg(body, nome)
        rel["tcgplayer"][k] = "gravado" if lake.put_if_absent(k, body) else "ja_existia"

    # --- PTAX: o dia e, se faltar, os últimos dias (recupera lacunas; a PTAX é histórica) ---
    for i in range(ptax_lookback, -1, -1):
        d = hoje - timedelta(days=i)
        k = raw_key("bcb_ptax", gid, d, "cotacao.json")
        if lake.exists(k):
            rel["bcb_ptax"][k] = "ja_existia"
            continue
        params = {"@moeda": "'USD'", "@dataCotacao": f"'{d:%m-%d-%Y}'", "$format": "json"}
        body = fetcher.get(PTAX_URL, params=params)
        if "value" not in json.loads(body):
            raise ValueError(f"PTAX de {d} sem campo 'value'")
        rel["bcb_ptax"][k] = "gravado" if lake.put_if_absent(k, body) else "ja_existia"

    # --- CDI: janela dos últimos dias (a taxa de um dia útil só sai na manhã seguinte) ---
    k = raw_key("bcb_cdi", gid, hoje, "cdi.json")
    if lake.exists(k):
        rel["bcb_cdi"][k] = "ja_existia"
    else:
        params = {
            "formato": "json",
            "dataInicial": f"{hoje - timedelta(days=cdi_window):%d/%m/%Y}",
            "dataFinal": f"{hoje:%d/%m/%Y}",
        }
        body = fetcher.get(CDI_URL, params=params)
        if not isinstance(json.loads(body), list):
            raise ValueError("CDI: resposta inesperada")
        rel["bcb_cdi"][k] = "gravado" if lake.put_if_absent(k, body) else "ja_existia"

    for fonte, itens in rel.items():
        novos = sum(1 for v in itens.values() if v == "gravado")
        log.info("%s: %d gravado(s), %d já existia(m)", fonte, novos, len(itens) - novos)
    return rel


def colecoes_ocupadas(lake: BaseLake) -> list[int]:
    """Lista os group_id que já têm pasta em raw/tcgplayer/ (para escolher coleção sem conflito)."""
    out = []
    for p in lake.list_prefixes("raw/tcgplayer/"):
        m = re.search(r"group_id=(\d+)/", p)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)
