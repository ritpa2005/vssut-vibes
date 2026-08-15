#!/bin/bash
# start.sh — production startup script
#
# Place this at the project root (same level as app/).
# Run with: bash start.sh
#
# Worker formula: (2 × CPU cores) + 1
# 1 core  → 3 workers
# 2 cores → 5 workers  (most basic VPS)
# 4 cores → 9 workers  (recommended for 1000 users)
#
# To check your CPU count: nproc
 
WORKERS=${WORKERS:-5}       # default 5 — override with: WORKERS=9 bash start.sh
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}
LOG_LEVEL=${LOG_LEVEL:-info}
 
echo "Starting VSSUT Vibes API"
echo "  Workers:   $WORKERS"
echo "  Host:      $HOST:$PORT"
echo "  Log level: $LOG_LEVEL"
 
uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    --proxy-headers \          # trust X-Forwarded-For from nginx/Cloudflare
    --forwarded-allow-ips="*"  # required when behind a reverse proxy