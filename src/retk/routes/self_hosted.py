import os

from fastapi import APIRouter, HTTPException, FastAPI
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from retk import const, config
from retk.logger import logger
from retk.routes import utils

r_prefix = "/r"
r_router = APIRouter(
    prefix=r_prefix,
    tags=["self_hosted"],
    responses={404: {"description": "Not found"}},
)

home_router = APIRouter(
    tags=["self_hosted_home"],
    responses={404: {"description": "Not found"}},
)

node_file_router = APIRouter(
    prefix="/files",
    tags=["self_hosted_files"],
    responses={404: {"description": "Not found"}},
)


@r_router.get("/", response_class=HTMLResponse)
@r_router.get("/sauth", response_class=HTMLResponse)
@r_router.get("/{path}", response_class=HTMLResponse)
@r_router.get("/plugin/{pid}", response_class=HTMLResponse)
@r_router.get("/n/{nid}", response_class=HTMLResponse)
async def app_page() -> HTMLResponse:
    if not config.is_local_db():
        raise HTTPException(status_code=404, detail="only support local storage")
    content = (const.settings.FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
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


@home_router.get("/", response_class=RedirectResponse)
async def index() -> RedirectResponse:
    return RedirectResponse(url=r_prefix)


# no /r/ needed, only use in local
@node_file_router.get(
    "/{fid}",
    status_code=200,
    response_class=FileResponse,
)
async def user_data(
        fid: str = utils.ANNOTATED_FID
) -> FileResponse:
    if not config.is_local_db():
        raise HTTPException(status_code=404, detail="only support local storage")
    prefix = config.get_settings().RETHINK_LOCAL_STORAGE_PATH
    return FileResponse(
        path=prefix / const.settings.DOT_DATA / "files" / fid,
        status_code=200,
    )


def mount_static(app: FastAPI):
    try:
        for name in ["css", "js", "img", "dist"]:
            app.mount(
                f"{r_prefix}/{name}",
                StaticFiles(directory=const.settings.FRONTEND_DIR / name),
                name=name,
            )
    except RuntimeError:
        logger.debug("mount frontend failed, the frontend files is in somewhere else")
