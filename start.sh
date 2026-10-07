#!/bin/sh
set -e

echo "=== Starting Rhythm Backend Container ==="

# Check if bgutil PO Token Provider build exists and start it on localhost:4416
if [ -f "/opt/bgutil/server/build/main.js" ]; then
    echo "Starting bgutil PO Token Provider on localhost:4416..."
    (cd /opt/bgutil/server && node build/main.js -H 127.0.0.1 -p 4416 &)
    sleep 3
    if curl -s http://127.0.0.1:4416/ping > /dev/null 2>&1; then
        echo "bgutil PO Token Provider is active and responding on http://127.0.0.1:4416/ping"
    else
        echo "Warning: bgutil PO Token Provider did not respond to /ping on startup"
    fi
elif [ -f "/opt/bgutil/server/dist/main.js" ]; then
    echo "Starting bgutil PO Token Provider on localhost:4416..."
    (cd /opt/bgutil/server && node dist/main.js -H 127.0.0.1 -p 4416 &)
    sleep 3
else
    echo "Notice: bgutil PO Token Provider build not found at /opt/bgutil/server/build/main.js"
fi

echo "Starting FastAPI on port ${PORT:-8000}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}"

