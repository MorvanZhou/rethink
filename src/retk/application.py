import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from retk import const, config, safety, utils
from retk.controllers.oauth import init_oauth_provider_map
from retk.controllers.self_hosted import notice_new_pkg_version
from retk.core import scheduler
from retk.core.files.importing import async_tasks
from retk.logger import logger, add_rotating_file_handler
from retk.plugins.register import register_official_plugins
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
    account,
    manager,
    statistic,
    notice,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # on startup
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

    # schedule job
    scheduler.start()
    scheduler.init_tasks()

    # init oauth provider map
    init_oauth_provider_map()

    # notice new pkg version
    if config.is_local_db():
        await notice_new_pkg_version()

    # register official plugins
    register_official_plugins()

    # local finish up
    utils.local_finish_up()

    yield

    # on shutdown
    scheduler.stop()
    await client.close()
    await client.search.close()
    logger.debug("fastapi shutdown event: db and searcher closed")

    async_tasks.stop()
    logger.debug("fastapi shutdown event: async_tasks stopped")


app = FastAPI(
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
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

for r in [
    user,
    oauth,
    node,
    recent,
    trash,
    app_captcha,
    files,
    plugin,
    account,
    manager,
    statistic,
    notice,
]:
    app.include_router(r.router)

# self-hosted
app.include_router(self_hosted.r_router)
app.include_router(self_hosted.node_file_router)
app.include_router(self_hosted.home_router)
self_hosted.mount_static(app=app)
