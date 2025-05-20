import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"

# Worker processes
workers = 2  # Reduced from 4 to 2 for better memory management
worker_class = 'gevent'
timeout = 30
keepalive = 5
worker_connections = 1000

# Memory management
max_requests = 1000
max_requests_jitter = 50
worker_tmp_dir = "/dev/shm"  # Use RAM for temporary files

# Logging
loglevel = "debug"
accesslog = "logs/access.log"
errorlog = "logs/error.log"

# Process naming
proc_name = 'chocomap'

# Server mechanics
daemon = False
pidfile = "gunicorn.pid"

# Server hooks
def pre_exec(server):
    """Remove stale PID file on restart."""
    try:
        os.remove(server.pidfile)
    except OSError:
        pass

def on_starting(server):
    """Log when server starts."""
    server.log.info("Starting ChocoMap server")

def on_exit(server):
    """Log when server exits."""
    server.log.info("Stopping ChocoMap server")

def worker_int(worker):
    """Log when worker receives SIGINT or SIGQUIT."""
    worker.log.info("Worker received SIGINT or SIGQUIT")

def worker_abort(worker):
    """Log when worker receives SIGABRT."""
    worker.log.info("Worker received SIGABRT") 