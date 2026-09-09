#!/bin/bash
# ECON API (Django ASGI via uvicorn) on 127.0.0.1:8000 — persistent local service.
set -u
cd /home/porus/ECON || exit 1
export ECON_RELOAD=0
exec /home/porus/ECON/.venv/bin/econom start
