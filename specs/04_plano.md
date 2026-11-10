# 04 · Plano técnico (CREATE: Plan)

| Módulo | Responsabilidade | Requisitos |
|---|---|---|
| `config.py` | Catálogo de coleções, variáveis de ambiente | RNF-03 |
| `storage.py` | S3 (boto3) e backend local; `put_if_absent` | RF-02, RNF-01 |
| `http.py` / `collect.py` | Coleta educada, frescor, lookback da PTAX | RF-01, RF-02, RNF-02 |
| `models.py` / `silver.py` | Pydantic, parsing, quarentena, Parquet tipado | RF-03, RF-04, RNF-05 |
| `gold.py` | Staging, dimensões, fatos, `ASOF JOIN` da PTAX | RF-05, RF-06 |
| `analytics.py` | As cinco perguntas (funções puras sobre DataFrame) | RF-07 a RF-12 |
| `portfolio.py` / `pipeline.py` | Cinco carteiras, métricas, placar, orquestração | RF-13 a RF-15, RNF-04 |
| `dashboard/app.py` | Streamlit | RF-07 a RF-15 |
| `demo.py` | Dados sintéticos **só locais** para desenvolvimento | — |

**Fluxo diário (agendador, 18:30 BRT):** `collect` → `silver` (todos os dias do bruto) → `gold` (silver da turma) → `portfolio`.

**Riscos e mitigações:** TCGCSV atrasado (guarda de frescor, exit 2); PTAX ausente em fim de semana/feriado (ASOF + lookback);
colega com tipo divergente (`TRY_CAST`, `union_by_name`); dia perdido (lacuna declarada, nunca preenchida com dado inventado).
