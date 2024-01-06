import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from rethink import const, config
from rethink.logger import logger, add_rotating_file_handler
from .models import database
from .routes import (
    user,
    oauth,
    node,
    search,
    trash,
    verification,
    files,
    email,
)

app = FastAPI(
    docs_url="/docs",
    openapi_url="/openapi.json",
)

if os.getenv("VUE_APP_MODE", "local") not in ["development", "local"]:
    allow_origins = [
        "https://rethink.run",
        "https://www.rethink.run",
    ]
    csp_local = ""
else:
    allow_origins = [
        "*",
    ]
    csp_local = " http://localhost:* http://127.0.0.1:* "


class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        csp_header = "default-src 'self'; " \
                     f"script-src 'self' 'unsafe-inline' 'unsafe-eval' {csp_local} https://www.googletagmanager.com; " \
                     f"style-src 'self' 'unsafe-inline' 'report-sample' {csp_local}; " \
                     "img-src * data: blob:; " \
                     f"connect-src 'self' {csp_local} https://www.google-analytics.com;"
        response.headers["Content-Security-Policy"] = csp_header
        return response


class FrameOptionsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Captcha-Token"],
)
app.add_middleware(CSPMiddleware)
app.add_middleware(FrameOptionsMiddleware)

app.include_router(node.router)
app.include_router(user.router)
app.include_router(oauth.router)
app.include_router(search.router)
app.include_router(trash.router)
app.include_router(verification.router)
app.include_router(files.router)
app.include_router(email.router)


@app.on_event("startup")
async def startup_event():
    if not config.is_local_db():
        add_rotating_file_handler(
            log_dir=const.RETHINK_DIR.parent.parent / "logs",
            max_bytes=10 * 1024 * 1024,
            backup_count=10,
        )
    logger.debug(f'startup_event LOCAL_STORAGE_PATH: {os.environ.get("LOCAL_STORAGE_PATH")}')
    logger.debug(f'startup_event VUE_APP_MODE: {os.environ.get("VUE_APP_MODE")}')
    logger.debug(f'startup_event VUE_APP_API_PORT: {os.environ.get("VUE_APP_API_PORT")}')
    logger.debug(f'startup_event VUE_APP_LANGUAGE: {os.environ.get("VUE_APP_LANGUAGE")}')
    await database.init()
    logger.info("db initialized")


@app.on_event("shutdown")
async def shutdown_event():
    try:
        await database.searcher().es.close()
    except (AttributeError, ValueError):
        pass
    logger.info("db closed")


try:
    for name in ["css", "js", "img", "dist"]:
        app.mount(
            f"/{name}",
            StaticFiles(directory=const.FRONTEND_DIR / name),
            name=name,
        )
except RuntimeError:
    logger.info("mount frontend failed")


@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
@app.get("/about", response_class=HTMLResponse)
@app.get("/r", response_class=HTMLResponse)
@app.get("/r/{path}", response_class=HTMLResponse)
@app.get("/n/{nid}", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    content = (const.FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    content += f"<script>window.VUE_APP_API_PORT = {os.getenv('VUE_APP_API_PORT')}</script>"
    return HTMLResponse(
        content=content,
        status_code=200,
    )


@app.get("/files/{fid}", response_class=FileResponse)
async def user_data(
        fid: str,
) -> FileResponse:
    if config.is_local_db():
        prefix = config.get_settings().LOCAL_STORAGE_PATH
    else:
        raise HTTPException(status_code=404, detail="only support local storage")
    return FileResponse(
        path=prefix / ".data" / "files" / fid,
        status_code=200,
    )
