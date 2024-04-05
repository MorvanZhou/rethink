import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from rethink import const, config, safety, utils
from rethink.logger import logger, add_rotating_file_handler
from rethink.plugins.register import register_official_plugins
from .models.client import client
from .routes import (
    user,
    oauth,
    node,
    search,
    trash,
    verification,
    files,
    email,
    plugin,
    self_hosted,
)

app = FastAPI(
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=safety.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Captcha-Token"],
)
app.add_middleware(safety.CSPMiddleware)
app.add_middleware(safety.FrameOptionsMiddleware)

app.include_router(node.router)
app.include_router(user.router)
app.include_router(oauth.router)
app.include_router(search.router)
app.include_router(trash.router)
app.include_router(verification.router)
app.include_router(files.router)
app.include_router(email.router)
app.include_router(plugin.router)
app.include_router(self_hosted.router)

try:
    for name in ["css", "js", "img", "dist"]:
        app.mount(
            f"/{name}",
            StaticFiles(directory=const.FRONTEND_DIR / name),
            name=name,
        )
except RuntimeError:
    logger.debug("mount frontend failed, the frontend files is in somewhere else")


@app.on_event("startup")
async def startup_event():
    if not config.is_local_db():
        add_rotating_file_handler(
            log_dir=const.RETHINK_DIR.parent.parent / "logs",
            max_bytes=10 * 1024 * 1024,
            backup_count=10,
        )
    logger.debug(f'startup_event RETHINK_LOCAL_STORAGE_PATH: {os.environ.get("RETHINK_LOCAL_STORAGE_PATH")}')
    logger.debug(f'startup_event VUE_APP_MODE: {os.environ.get("VUE_APP_MODE")}')
    logger.debug(f'startup_event VUE_APP_API_PORT: {os.environ.get("VUE_APP_API_PORT")}')
    logger.debug(f'startup_event VUE_APP_LANGUAGE: {os.environ.get("VUE_APP_LANGUAGE")}')
    await client.init()
    logger.debug("db initialized")

    register_official_plugins()

    # local finish up
    utils.local_finish_up()
