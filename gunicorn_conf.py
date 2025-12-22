import os

# Gunicorn configuration file
import multiprocessing

# Bind to 0.0.0.0:PORT or 0.0.0.0:8000 if PORT is not set
port = os.getenv("PORT", "8000")
bind = f"0.0.0.0:{port}"

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
