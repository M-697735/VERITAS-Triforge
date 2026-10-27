#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "[VERITAS] Checking frontend build..."
if [ ! -f "frontend/dist/index.html" ]; then
    echo "[VERITAS] Building frontend assets..."
    cd frontend
    npm install
    npm run build
    cd ..
fi

echo "[VERITAS] Launching backend server and opening browser..."
python backend/run.py "$@"

