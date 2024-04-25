import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from retk import const, config, safety, utils
from retk.core import async_task
from retk.logger import logger, add_rotating_file_handler
from .models.client import client
from .routes import (
    user,
    oauth,
    node,
    recent,
    trash,
    app_captcha,
    files,
    plugin,
    self_hosted,
    app_system,
    account,
    admin,
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
app.include_router(recent.router)
app.include_router(trash.router)
app.include_router(app_captcha.router)
app.include_router(files.router)
app.include_router(plugin.router)
app.include_router(app_system.router)
app.include_router(account.router)
app.include_router(admin.router)

# self hosted
app.include_router(self_hosted.r_router)
app.include_router(self_hosted.node_file_router)
app.include_router(self_hosted.home_router)
self_hosted.mount_static(app=app)


@app.on_event("startup")
async def startup_event():
    if not config.is_local_db():
        add_rotating_file_handler(
            log_dir=const.settings.RETHINK_DIR.parent.parent / "logs",
            max_bytes=10 * 1024 * 1024,
            backup_count=10,
        )
    logger.debug(f'startup_event RETHINK_LOCAL_STORAGE_PATH: {os.environ.get("RETHINK_LOCAL_STORAGE_PATH")}')
    logger.debug(f'startup_event VUE_APP_MODE: {os.environ.get("VUE_APP_MODE")}')
    logger.debug(f'startup_event VUE_APP_API_PORT: {os.environ.get("VUE_APP_API_PORT")}')
    logger.debug(f'startup_event RETHINK_DEFAULT_LANGUAGE: {os.environ.get("RETHINK_DEFAULT_LANGUAGE")}')
    await client.init()
    logger.debug("db initialized")

    # local finish up
    utils.local_finish_up()

    # async threading task
    async_task.init()
