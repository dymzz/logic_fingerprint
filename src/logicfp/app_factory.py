from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.staticfiles import StaticFiles

from ._version import __version__
from .router import build_router
from .lifespan import build_lifespan
from .runtime import (
    LogicFingerprintRuntime,
    build_demo_runtime,
    build_production_runtime,
)


DOCS_STATIC_DIR = Path(__file__).resolve().parents[2] / "static" / "dist"


def _create_app_from_runtime(runtime: LogicFingerprintRuntime) -> FastAPI:
    app = FastAPI(
        title="logicfp",
        version=__version__,
        lifespan=build_lifespan(runtime, interval_seconds=1.0),
        docs_url=None,
        redoc_url=None,
    )
    app.state.runtime = runtime
    app.state.runtime_config = runtime.config
    app.state.runtime_settings = runtime.settings
    if DOCS_STATIC_DIR.exists():
        app.mount(
            "/static-docs",
            StaticFiles(directory=DOCS_STATIC_DIR),
            name="static-docs",
        )

    @app.get("/docs", include_in_schema=False)
    def swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static-docs/swagger-ui-bundle.js",
            swagger_css_url="/static-docs/swagger-ui.css",
            swagger_favicon_url="/static-docs/favicon-32x32.png",
            swagger_ui_parameters={
                "presets": [
                    "SwaggerUIBundle.presets.apis",
                    "SwaggerUIStandalonePreset",
                ],
            },
        )

    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    app.include_router(build_router(runtime))
    return app


def create_app(
    *,
    runtime: LogicFingerprintRuntime | None = None,
    runtime_kwargs: dict[str, Any] | None = None,
) -> FastAPI:
    runtime = runtime or build_production_runtime(**(runtime_kwargs or {}))
    return _create_app_from_runtime(runtime)


def create_demo_app(
    *,
    runtime: LogicFingerprintRuntime | None = None,
    runtime_kwargs: dict[str, Any] | None = None,
) -> FastAPI:
    runtime = runtime or build_demo_runtime(**(runtime_kwargs or {}))
    return _create_app_from_runtime(runtime)


app = create_app()

