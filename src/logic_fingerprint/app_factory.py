from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.staticfiles import StaticFiles

from .api import build_router
from .lifespan import build_lifespan
from .runtime import build_runtime


DOCS_STATIC_DIR = Path(__file__).resolve().parents[2] / "static" / "dist"


def create_app() -> FastAPI:
    runtime = build_runtime()
    app = FastAPI(
        title="Logic Fingerprint System",
        version="1.0.0",
        lifespan=build_lifespan(runtime, interval_seconds=1.0),
        docs_url=None,
        redoc_url=None,
    )
    app.state.runtime = runtime
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


app = create_app()
