"""Gunicorn settings for the backend and Standard Deployment images.

The bind address is passed on the command line by supervisord because it differs per image.

Memory: the app is loaded once in the master (``preload_app``) and the workers are forked from
it, so the ~100 MB of imported code (Django, GDAL, DRF, ...) is shared between workers instead of
being duplicated. Preloading alone does not share much, because Python's reference counting and
garbage collector write to every object and force the kernel to copy the pages. ``gc.freeze()``
moves everything loaded so far out of the collector's reach, which is what lets the pages stay
shared. Measured on the Standard Deployment image: ~300 MB -> ~185 MB for the web workers.
"""

import gc
import os


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ.get(name, default)))
    except ValueError:
        return default


workers = _int_env('GUNICORN_WORKERS', 2)
threads = _int_env('GUNICORN_THREADS', 4)
timeout = _int_env('GUNICORN_TIMEOUT', 120)

# Must outlast Node fetch's 4s idle-socket reuse, or the frontend can reuse a connection gunicorn
# is closing ("fetch failed: other side closed"). gthread's default is 2s.
keepalive = 5

preload_app = True

# Recycle a worker after this many requests so memory it grew by a heavy request (GPX parsing,
# image decoding, PDF rendering) is eventually returned to the OS. Jitter staggers the restarts so
# both workers are never recycling at once. GUNICORN_MAX_REQUESTS=0 turns recycling off.
#
# This is a safety net, so it is deliberately high: measured on the Standard Deployment image,
# gthread drops about one already-accepted connection per recycle, which is a failed request.
# At 1000 that was ~0.08% of requests; at 10000 it is ~0.008%.
max_requests = _int_env('GUNICORN_MAX_REQUESTS', 10000, minimum=0)
max_requests_jitter = max_requests // 10

# Worker heartbeat files go to tmpfs rather than the container's writable layer.
worker_tmp_dir = '/dev/shm'

accesslog = None
errorlog = '-'


def when_ready(server):
    """Runs in the master once the app is loaded and before any worker is forked."""
    # Importing the URLconf imports every view module, so do it here rather than in each worker
    # on its first request, where the pages would be private to that worker.
    from django.urls import get_resolver

    get_resolver().url_patterns

    gc.collect()
    gc.freeze()


def pre_fork(server, worker):
    """Do not hand open sockets to children: a forked worker must open its own."""
    from django.core.cache import caches
    from django.db import connections

    connections.close_all()
    for cache in caches.all(initialized_only=True):
        close = getattr(cache, 'close', None)
        if close:
            close()
