# gunicorn.conf.py
# ─────────────────────────────────────────────────────────────────────────────
# Gunicorn server configuration
#
# The keep-alive thread is started at module-import time inside app.py.
# When gunicorn forks worker processes, Python threads started in the master
# process are NOT carried over to the workers (only the forking thread
# survives a fork(2)).  The post_fork hook below guarantees that every worker
# starts its own keep-alive thread regardless of whether --preload is used.
# ─────────────────────────────────────────────────────────────────────────────


def post_fork(server, worker):
    """Restart the keep-alive thread inside every newly forked worker."""
    # Import lazily so gunicorn can load this config before the app is ready.
    from app import _start_keep_alive
    _start_keep_alive()
