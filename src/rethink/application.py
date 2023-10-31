import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from rethink import const
from rethink.logger import logger
from .models import database
from .routes import (
    user,
    oauth,
    node,
    search,
    trash,
    verification,
    files,
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
else:
    allow_origins = [
        "*",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Captcha-Token"],
)

app.include_router(node.router)
app.include_router(user.router)
app.include_router(oauth.router)
app.include_router(search.router)
app.include_router(trash.router)
app.include_router(verification.router)
app.include_router(files.router)


@app.on_event("startup")
async def startup_event():
    database.init()
    logger.info("db initialized")


app.mount(
    "/css",
    StaticFiles(directory=const.FRONTEND_DIR / "css"),
    name="css",
)
app.mount(
    "/js",
    StaticFiles(directory=const.FRONTEND_DIR / "js"),
    name="js",
)
app.mount(
    "/img",
    StaticFiles(directory=const.FRONTEND_DIR / "img"),
    name="img",
)


@app.get("/", response_class=HTMLResponse)
@app.get("/r", response_class=HTMLResponse)
@app.get("/user", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    content = (const.FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    content += f"<script>window.VUE_APP_API_PORT = {os.getenv('VUE_APP_API_PORT')}</script>"
    return HTMLResponse(
        content=content,
        status_code=200,
    )
