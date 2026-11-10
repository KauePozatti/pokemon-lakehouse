"""Configuração do pipeline (variáveis de ambiente) e catálogo de coleções."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

try:  # python-dotenv é opcional em produção (variáveis vêm do job)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

# Coleções do projeto (página da disciplina, consultadas em 21/10/2026).
COLECOES: dict[str, dict] = {
    "TEF": {"group_id": 23381, "nome": "SV05: Temporal Forces", "data_lancamento": date(2024, 3, 22)},
    "TWM": {"group_id": 23473, "nome": "SV06: Twilight Masquerade", "data_lancamento": date(2024, 5, 24)},
    "SFA": {"group_id": 23529, "nome": "SV: Shrouded Fable", "data_lancamento": date(2024, 8, 2)},
    "SCR": {"group_id": 23537, "nome": "SV07: Stellar Crown", "data_lancamento": date(2024, 9, 13)},
    "SSP": {"group_id": 23651, "nome": "SV08: Surging Sparks", "data_lancamento": date(2024, 11, 8)},
    "PRE": {"group_id": 23821, "nome": "SV: Prismatic Evolutions", "data_lancamento": date(2025, 1, 17)},
    "JTG": {"group_id": 24073, "nome": "SV09: Journey Together", "data_lancamento": date(2025, 3, 28)},
    "DRI": {"group_id": 24269, "nome": "SV10: Destined Rivals", "data_lancamento": date(2025, 5, 30)},
    "BLK": {"group_id": 24325, "nome": "SV: Black Bolt", "data_lancamento": date(2025, 7, 18)},
    "WHT": {"group_id": 24326, "nome": "SV: White Flare", "data_lancamento": date(2025, 7, 18)},
    "MEG": {"group_id": 24380, "nome": "ME01: Mega Evolution", "data_lancamento": date(2025, 9, 26)},
    "PFL": {"group_id": 24448, "nome": "ME02: Phantasmal Flames", "data_lancamento": date(2025, 11, 14)},
    "ASC": {"group_id": 24541, "nome": "ME: Ascended Heroes", "data_lancamento": date(2026, 1, 30)},
    "POR": {"group_id": 24587, "nome": "ME03: Perfect Order", "data_lancamento": date(2026, 3, 27)},
    "CRI": {"group_id": 24655, "nome": "ME04: Chaos Rising", "data_lancamento": date(2026, 5, 22)},
    "PBL": {"group_id": 24688, "nome": "ME05: Pitch Black", "data_lancamento": date(2026, 7, 17)},
    "30C": {"group_id": 24722, "nome": "ME: 30th Celebration", "data_lancamento": date(2026, 9, 16)},
}
GROUP_TO_SIGLA = {v["group_id"]: k for k, v in COLECOES.items()}

CATEGORY_ID = 3  # Pokémon no TCGplayer


@dataclass(frozen=True)
class Settings:
    backend: str = "s3"  # "s3" | "local"
    bucket: str = "tcg"
    endpoint_url: str = "https://s3.afonsolelis.tech"
    access_key: str = ""
    secret_key: str = ""
    region: str = "us-east-1"
    local_root: Path = Path("data_local")
    sigla: str = "DRI"
    group_id: int = 24269
    responsavel: str = ""
    taxa_venda: float = 0.15
    pause_s: float = 0.2  # o TCGCSV pede pelo menos 100 ms entre chamadas

    @property
    def user_agent(self) -> str:
        return f"colecao-{self.sigla.lower()}/1.0"

    @property
    def colecao(self) -> dict:
        return COLECOES[self.sigla]


def load_settings(**overrides) -> Settings:
    sigla = os.getenv("COLECAO_SIGLA", "DRI").upper()
    if sigla not in COLECOES:
        raise ValueError(f"COLECAO_SIGLA inválida: {sigla}. Opções: {', '.join(COLECOES)}")
    base = dict(
        backend=os.getenv("POKELAKE_BACKEND", "s3"),
        bucket=os.getenv("S3_BUCKET", "tcg"),
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "https://s3.afonsolelis.tech"),
        access_key=os.getenv("S3_ACCESS_KEY", ""),
        secret_key=os.getenv("S3_SECRET_KEY", ""),
        region=os.getenv("S3_REGION", "us-east-1"),
        local_root=Path(os.getenv("LOCAL_ROOT", "data_local")),
        sigla=sigla,
        group_id=COLECOES[sigla]["group_id"],
        responsavel=os.getenv("RESPONSAVEL", ""),
        taxa_venda=float(os.getenv("TAXA_VENDA", "0.15")),
    )
    base.update(overrides)
    if "sigla" in overrides and "group_id" not in overrides:
        base["group_id"] = COLECOES[base["sigla"]]["group_id"]
    return Settings(**base)
