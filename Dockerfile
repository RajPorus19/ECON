FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.development

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY config /app/config
COPY apps /app/apps
COPY core /app/core
COPY econom /app/econom
COPY host_agent /app/host_agent
COPY manage.py /app/manage.py
COPY plugins /app/plugins
COPY econom.yaml /app/econom.yaml
COPY docker /app/docker

RUN pip install --no-cache-dir . \
    && chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
