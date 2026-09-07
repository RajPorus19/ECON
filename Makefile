.PHONY: install test lint migrate seed up doctor web

install:
	uv venv --python 3.12 .venv
	uv pip install -e ".[dev]" --python .venv/bin/python

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	.venv/bin/mypy core econom host_agent apps

migrate:
	.venv/bin/python manage.py migrate

seed:
	.venv/bin/python manage.py seed_defaults

up:
	docker compose up postgres redis

doctor:
	.venv/bin/econom doctor

web:
	cd web && pnpm install && pnpm test && pnpm build
