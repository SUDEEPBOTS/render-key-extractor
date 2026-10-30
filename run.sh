#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

export PYTHONPATH="$DIR:$PYTHONPATH"
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8090}"

echo "Starting Render Key Extractor on http://${HOST}:${PORT}"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --workers 1
