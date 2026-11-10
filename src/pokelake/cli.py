"""CLI: python -m pokelake <comando>."""
from __future__ import annotations

import argparse
import logging
import sys

from pokelake.collect import DadoDefasadoError, collect, colecoes_ocupadas
from pokelake.config import GROUP_TO_SIGLA, load_settings
from pokelake.db import connect
from pokelake.gold import build_gold
from pokelake.pipeline import build_portfolio, rebuild, run_daily
from pokelake.silver import build_silver
from pokelake.storage import make_lake


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pokelake")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-colecao", help="lista os group_id já ocupados em raw/tcgplayer/")
    c = sub.add_parser("collect", help="coleta o dia (bruto)")
    c.add_argument("--allow-stale", action="store_true", help="grava mesmo se o TCGCSV ainda não atualizou")
    sub.add_parser("silver", help="bruto -> silver")
    sub.add_parser("gold", help="silver da turma -> gold dimensional")
    sub.add_parser("portfolio", help="calcula as cinco carteiras")
    sub.add_parser("rebuild", help="reconstrói silver + gold + carteira a partir do bruto")
    d = sub.add_parser("daily", help="coleta + rebuild (é o que o agendador roda)")
    d.add_argument("--allow-stale", action="store_true")
    dm = sub.add_parser("demo", help="dados SINTÉTICOS locais (nunca no lake da turma)")
    dm.add_argument("--dias", type=int, default=30)
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = load_settings()
    if args.cmd == "demo":
        from dataclasses import replace

        from pokelake.demo import seed_demo

        s = replace(s, backend="local", local_root=s.local_root.parent / "data_demo")
        lake = make_lake(s)
        grupos = seed_demo(lake, s, n_dias=args.dias)
        res = rebuild(lake, s, grupos)
        print(res["carteira"]["metricas"].to_string(index=False))
        print(f"\nDemo pronta em {s.local_root}. Rode: POKELAKE_BACKEND=local LOCAL_ROOT={s.local_root} streamlit run dashboard/app.py")
        return 0

    lake = make_lake(s)
    print(f"Coleção: {s.sigla} (group_id={s.group_id}) | backend={s.backend} | bucket={s.bucket}")
    try:
        if args.cmd == "check-colecao":
            ocupados = colecoes_ocupadas(lake)
            for g in ocupados:
                print(f"  group_id={g} ({GROUP_TO_SIGLA.get(g, '?')})")
            print("Sua coleção já tem pasta no lake." if s.group_id in ocupados else "Sua coleção está livre.")
        elif args.cmd == "collect":
            collect(lake, s, allow_stale=args.allow_stale)
        elif args.cmd == "silver":
            build_silver(lake, s)
        elif args.cmd == "gold":
            build_gold(lake, s, connect(lake, s))
        elif args.cmd == "portfolio":
            build_portfolio(lake, s)
        elif args.cmd == "rebuild":
            rebuild(lake, s)
        elif args.cmd == "daily":
            run_daily(lake, s, allow_stale=args.allow_stale)
    except DadoDefasadoError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    return 0
