# Render web service launcher.
# - workers=1: multiple sync workers each import the whole app (pandas/numpy/
#   weasyprint/google-genai) and each runs a full DB schema migration at boot —
#   that OOMs a 512MB free instance (WORKER TIMEOUT -> SIGKILL). Threads handle
#   concurrency instead.
# - timeout=180: default 30s is too short for US Postgres latency + dashboard
#   polling; a slow request would get the worker killed.
# - max-requests: recycle workers to prevent memory creep.
web: gunicorn ConnectLink:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180 --graceful-timeout 60 --max-requests 500 --max-requests-jitter 50
