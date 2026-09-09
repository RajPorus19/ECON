#!/bin/bash
# ECON web UI (TanStack Start / Vite) on 127.0.0.1:3000 — persistent local service.
set -u
export PATH="/home/porus/.nvm/versions/node/v25.8.2/bin:$PATH"
cd /home/porus/ECON/web || exit 1
exec pnpm dev --host 127.0.0.1
