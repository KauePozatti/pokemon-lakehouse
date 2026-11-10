# Imagem do coletor diário (Railway Cron Job ou qualquer agendador de containers).
# Railway: Settings > Cron Schedule = "30 21 * * *" (21:30 UTC = 18:30 BRT).
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# O job termina sozinho (exit 0 em sucesso, 2 se o TCGCSV ainda não atualizou).
CMD ["python", "-m", "pokelake", "daily"]
