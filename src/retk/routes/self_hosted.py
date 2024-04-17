import os

from fastapi import APIRouter, HTTPException, FastAPI
from fastapi.responses import HTMLResponse, FileResponse
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


@router.get("/", response_class=HTMLResponse)
@router.get("/sauth", response_class=HTMLResponse)
@router.get("/docs", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
@router.get("/about", response_class=HTMLResponse)
@router.get("/r", response_class=HTMLResponse)
@router.get("/r/{path}", response_class=HTMLResponse)
@router.get("/r/plugin/{pid}", response_class=HTMLResponse)
@router.get("/n/{nid}", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    content = (const.FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    if os.getenv("RETHINK_SERVER_PASSWORD", None) is not None:
        req_password = "window.VUE_APP_ONE_USER_REQUIRE_AUTH=1;"
    else:
        req_password = ""
    content += f"<script>window.VUE_APP_API_PORT={os.getenv('VUE_APP_API_PORT')};" \
               f"{req_password}</script>"
    return HTMLResponse(
        content=content,
        status_code=200,
    )


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
