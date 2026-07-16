FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    DATABASE_PATH=/data/ticketplus.db

RUN groupadd --system ticketplus && useradd --system --gid ticketplus ticketplus \
    && mkdir -p /app /data && chown ticketplus:ticketplus /app /data

WORKDIR /app
COPY --chown=ticketplus:ticketplus pyproject.toml ./
COPY --chown=ticketplus:ticketplus src ./src

USER ticketplus
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/ready', timeout=2)"]

CMD ["python", "-m", "ticketplus.http_api"]

