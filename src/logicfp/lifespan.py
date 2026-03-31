import threading
from contextlib import asynccontextmanager

def build_lifespan(runtime: object, interval_seconds: float = 5.0):
    @asynccontextmanager
    async def lifespan(app):
        stop_event = threading.Event()
        def loop():
            while not stop_event.is_set():
                runtime.heartbeat.beat()
                stop_event.wait(interval_seconds)
        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        app.state.heartbeat_stop_event = stop_event
        app.state.heartbeat_thread = thread
        try:
            yield
        finally:
            stop_event.set()
            thread.join(timeout=1.0)
    return lifespan
