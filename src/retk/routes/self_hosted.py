import os

from fastapi import APIRouter, HTTPException, FastAPI
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from retk import const, config
from retk.logger import logger
from retk.models.client import client
from retk.routes import utils

router = APIRouter(
    tags=["self_hosted"],
    responses={404: {"description": "Not found"}},
)


@router.on_event("shutdown")
async def shutdown_event():
    try:
        await client.search.es.close()
    except (AttributeError, ValueError):
        pass
    logger.debug("db closed")


@router.get("/sauth", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
@router.get("/r", response_class=HTMLResponse)
@router.get("/r/{path}", response_class=HTMLResponse)
@router.get("/r/plugin/{pid}", response_class=HTMLResponse)
@router.get("/n/{nid}", response_class=HTMLResponse)
async def app_page() -> HTMLResponse:
    content = (const.FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    script = f"window.VUE_APP_API_PORT={os.getenv('VUE_APP_API_PORT')};"
    language = os.getenv("RETHINK_DEFAULT_LANGUAGE")
    if language is not None:
        script += f"window.VUE_APP_LANGUAGE='{language}';"
    if os.getenv("RETHINK_SERVER_PASSWORD", None) is not None:
        script += "window.VUE_APP_ONE_USER_REQUIRE_AUTH=1;"
    script = f"<script>{script}</script>"

    return HTMLResponse(
        content=content + script,
        status_code=200,
    )


@router.get("/", response_class=RedirectResponse)
async def index() -> RedirectResponse:
    return RedirectResponse(url="/r")


@router.get(
    "/files/{fid}",
    status_code=200,
    response_class=FileResponse,
)
async def user_data(
        fid: str = utils.ANNOTATED_FID
) -> FileResponse:
    if config.is_local_db():
        prefix = config.get_settings().RETHINK_LOCAL_STORAGE_PATH
    else:
        raise HTTPException(status_code=404, detail="only support local storage")
    return FileResponse(
        path=prefix / ".data" / "files" / fid,
        status_code=200,
    )


def mount_static(app: FastAPI):
    try:
        for name in ["css", "js", "img", "dist"]:
            app.mount(
                f"/{name}",
                StaticFiles(directory=const.FRONTEND_DIR / name),
                name=name,
            )
    except RuntimeError:
        logger.debug("mount frontend failed, the frontend files is in somewhere else")
