#!/bin/bash
set -e

# Memory constraints for 512MB container
export NODE_OPTIONS="--max-old-space-size=48"
export MALLOC_ARENA_MAX=2
export PYTHONUNBUFFERED=1

echo "Container starting in low-memory profile (512MB optimized)..."

# Render dynamically provides PORT environment variable
PORT="${PORT:-8090}"
HOST="${HOST:-0.0.0.0}"

echo "Starting Uvicorn server on http://${HOST}:${PORT}..."
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --workers 1
