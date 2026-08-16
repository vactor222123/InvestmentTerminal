FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/application \
    INVESTMENT_TERMINAL_RUNTIME_DATA_ROOT=/runtime \
    INVESTMENT_TERMINAL_KNOWLEDGE_DATABASE=/runtime/knowledge.db \
    INVESTMENT_TERMINAL_PROVIDER_USAGE_COST_DATABASE=/runtime/operational/provider_usage_cost.db \
    INVESTMENT_TERMINAL_GROUNDED_GENERATION_DATABASE=/runtime/operational/grounded_generations.db

WORKDIR /application

COPY requirements.lock /application/requirements.lock

RUN python -m pip install --no-cache-dir --require-hashes \
        -r /application/requirements.lock \
    && groupadd --system investment-terminal \
    && useradd \
        --system \
        --gid investment-terminal \
        --home-dir /nonexistent \
        --no-create-home \
        --shell /usr/sbin/nologin \
        investment-terminal \
    && mkdir -p \
        /runtime/operational \
        /backups \
        /config \
        /secrets \
    && chown -R investment-terminal:investment-terminal \
        /runtime \
        /backups \
    && chmod 0755 \
        /config \
        /secrets

COPY investment_terminal /application/investment_terminal

RUN chmod -R a-w /application

USER investment-terminal:investment-terminal

EXPOSE 8000

VOLUME ["/runtime", "/backups"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"]

CMD ["python", "-m", "investment_terminal.cli.server", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
