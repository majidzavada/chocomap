import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gevent'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "debug"

# Process naming
proc_name = 'chocomap'

# Server mechanics
daemon = False
pidfile = "gunicorn.pid"
umask = 0
user = None
group = None

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