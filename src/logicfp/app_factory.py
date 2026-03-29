from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

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
HTTPAppMode = Literal["production", "demo"]


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


def create_http_app(
    *,
    mode: HTTPAppMode = "production",
    runtime: LogicFingerprintRuntime | None = None,
    runtime_kwargs: dict[str, Any] | None = None,
) -> FastAPI:
    if runtime is not None and runtime_kwargs is not None:
        raise ValueError("Pass either 'runtime' or 'runtime_kwargs', not both.")

    if runtime is None:
        runtime_builders = {
            "production": build_production_runtime,
            "demo": build_demo_runtime,
        }
        try:
            runtime_builder = runtime_builders[mode]
        except KeyError as exc:
            raise ValueError(f"Unsupported HTTP app mode: {mode}") from exc
        runtime = runtime_builder(**(runtime_kwargs or {}))

    return _create_app_from_runtime(runtime)


def create_app(
    *,
    runtime: LogicFingerprintRuntime | None = None,
    runtime_kwargs: dict[str, Any] | None = None,
) -> FastAPI:
    return create_http_app(
        mode="production",
        runtime=runtime,
        runtime_kwargs=runtime_kwargs,
    )


def create_demo_app(
    *,
    runtime: LogicFingerprintRuntime | None = None,
    runtime_kwargs: dict[str, Any] | None = None,
) -> FastAPI:
    return create_http_app(
        mode="demo",
        runtime=runtime,
        runtime_kwargs=runtime_kwargs,
    )


app = create_http_app()

