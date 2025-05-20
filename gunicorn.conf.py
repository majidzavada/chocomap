import multiprocessing

# Server socket
bind = "0.0.0.0:8000"

# Worker processes
workers = 4
worker_class = 'gevent'
timeout = 30

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