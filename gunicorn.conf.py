import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = 'logs/gunicorn-access.log'
errorlog = 'logs/gunicorn-error.log'
loglevel = 'info'

# Process naming
proc_name = 'chocomap'

# SSL
# keyfile = 'path/to/keyfile'
# certfile = 'path/to/certfile'

# Server mechanics
daemon = False
pidfile = 'gunicorn.pid'
umask = 0
user = None
group = None
tmp_upload_dir = None

# Server hooks
def on_starting(server):
    """Log when server starts."""
    server.log.info("Starting Chocomap server")

def on_exit(server):
    """Log when server exits."""
    server.log.info("Stopping Chocomap server")

def worker_int(worker):
    """Log when worker receives SIGINT or SIGQUIT."""
    worker.log.info("Worker received SIGINT or SIGQUIT")

def worker_abort(worker):
    """Log when worker receives SIGABRT."""
    worker.log.info("Worker received SIGABRT") 