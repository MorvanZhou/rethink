from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from retk import safety
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
    ai,
)
from .routes.utils import on_shutdown, on_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()
    yield
    await on_shutdown()


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
    ai,
]:
    app.include_router(r.router)

# self-hosted
app.include_router(self_hosted.r_router)
app.include_router(self_hosted.node_file_router)
app.include_router(self_hosted.home_router)
self_hosted.mount_static(app=app)
