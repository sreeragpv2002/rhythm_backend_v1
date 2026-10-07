#!/bin/sh
set -e

echo "=== Starting Rhythm Backend Container ==="

# Check if bgutil PO Token Provider build exists and start it on localhost:4416
if [ -f "/opt/bgutil/server/build/main.js" ]; then
    echo "Starting bgutil PO Token Provider on localhost:4416..."
    node /opt/bgutil/server/build/main.js &
    echo "bgutil PO Token Provider launched in background (internal port 4416)"
    sleep 2
elif [ -f "/opt/bgutil/server/dist/main.js" ]; then
    echo "Starting bgutil PO Token Provider on localhost:4416..."
    node /opt/bgutil/server/dist/main.js &
    echo "bgutil PO Token Provider launched in background (internal port 4416)"
    sleep 2
else
    echo "Notice: bgutil PO Token Provider build not found at /opt/bgutil/server/build/main.js"
fi

echo "Starting FastAPI on port ${PORT:-8000}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}"
