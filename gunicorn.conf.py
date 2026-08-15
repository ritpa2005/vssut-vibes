# gunicorn.conf.py
#
# Alternative to start.sh — use Gunicorn with Uvicorn workers.
# Gunicorn is more production-hardened: handles worker crashes,
# graceful restarts, and process management better than bare Uvicorn.
#
# Install: pip install gunicorn
# Run:     gunicorn -c gunicorn.conf.py app.main:app

import multiprocessing

# ── Workers ───────────────────────────────────────────────────────────────────
workers     = (multiprocessing.cpu_count() * 2) + 1
worker_class = "uvicorn.workers.UvicornWorker"   # async workers for FastAPI

# ── Binding ───────────────────────────────────────────────────────────────────
bind        = "0.0.0.0:8000"
backlog     = 2048   # max pending connections in queue

# ── Timeouts ──────────────────────────────────────────────────────────────────
timeout          = 60    # kill worker if it doesn't respond in 60s
keepalive        = 5     # keep idle connections alive for 5s
graceful_timeout = 30    # give workers 30s to finish requests on shutdown

# ── Logging ───────────────────────────────────────────────────────────────────
loglevel    = "info"
accesslog   = "-"    # stdout
errorlog    = "-"    # stdout

# ── Process naming ────────────────────────────────────────────────────────────
proc_name   = "vssut-vibes"