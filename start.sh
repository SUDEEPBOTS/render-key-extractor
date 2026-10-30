#!/bin/bash
set -e

# Start Tor in background
echo "Starting Tor service..."
tor --RunAsDaemon 1 || /etc/init.d/tor start || true

# Wait for Tor SOCKS port to be ready
echo "Waiting for Tor SOCKS proxy on 127.0.0.1:9050..."
for i in {1..15}; do
    if curl -s --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip > /dev/null 2>&1; then
        echo "Tor is online and active!"
        break
    fi
    sleep 1
done

# Render dynamically provides PORT environment variable
PORT="${PORT:-8090}"
HOST="${HOST:-0.0.0.0}"

echo "Starting Uvicorn server on http://${HOST}:${PORT}..."
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --workers 1
