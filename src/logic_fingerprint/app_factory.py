from fastapi import FastAPI
from .api import build_router
from .lifespan import build_lifespan
from .runtime import build_runtime

def create_app() -> FastAPI:
    runtime = build_runtime()
    app = FastAPI(title="Logic Fingerprint System", version="1.0.0", lifespan=build_lifespan(runtime, interval_seconds=1.0))
    app.state.runtime = runtime
    app.include_router(build_router(runtime))
    return app

app = create_app()
