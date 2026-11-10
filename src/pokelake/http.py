"""Cliente HTTP educado: User-Agent próprio, pausa entre chamadas e novas tentativas."""
from __future__ import annotations

import time

import requests


class Fetcher:
    def __init__(self, user_agent: str, pause_s: float = 0.2, timeout: int = 60, retries: int = 3):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.pause_s = max(pause_s, 0.1)
        self.timeout = timeout
        self.retries = retries

    def get(self, url: str, params: dict | None = None) -> bytes:
        """Devolve o corpo ORIGINAL da resposta (bytes), para gravar sem alteração no bruto."""
        last: Exception | None = None
        for attempt in range(1, self.retries + 1):
            time.sleep(self.pause_s)
            try:
                r = self.session.get(url, params=params, timeout=self.timeout)
                if r.status_code >= 500:
                    raise requests.HTTPError(f"{r.status_code} em {url}")
                r.raise_for_status()
                return r.content
            except (requests.RequestException, OSError) as e:
                last = e
                time.sleep(2**attempt)
        raise RuntimeError(f"Falha ao buscar {url} após {self.retries} tentativas: {last}")
