from typing import List, Optional

from fastapi import APIRouter, UploadFile, Request

from rethink.controllers import schemas
from rethink.controllers.files import upload_files
from rethink.routes import utils

router = APIRouter(
    prefix="/api/files",
    tags=["files"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/obsidian",
    status_code=202,
    response_model=schemas.files.FileUploadResponse,
)
@utils.measure_time_spend
async def upload_obsidian_files(
        h: utils.ANNOTATED_HEADERS,
        files: List[UploadFile],
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.files.FileUploadResponse:
    return await upload_files.upload_obsidian_files(
        h=h,
        files=files,
    )


@router.post(
    path="/text",
    status_code=202,
    response_model=schemas.files.FileUploadResponse,
)
@utils.measure_time_spend
async def upload_text_files(
        h: utils.ANNOTATED_HEADERS,
        files: List[UploadFile],
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.files.FileUploadResponse:
    return await upload_files.upload_text_files(
        h=h,
        files=files,
    )


@router.post(
    path="/vditor",
    status_code=201,
    response_model=schemas.files.VditorFilesResponse,
)
@utils.measure_time_spend
async def vditor_upload(
        h: utils.ANNOTATED_HEADERS,
        req: Request,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.files.VditorFilesResponse:
    form = await req.form()
    file = form.get("file[]")
    return await upload_files.upload_file_vditor(
        h=h,
        file=file,
    )


@router.post(
    path="/vditor/images",
    status_code=201,
    response_model=schemas.files.VditorImagesResponse,
)
@utils.measure_time_spend
async def vditor_fetch_image(
        h: utils.ANNOTATED_HEADERS,
        req: schemas.files.ImageVditorFetchRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.files.VditorImagesResponse:
    return await upload_files.fetch_image_vditor(
        h=h,
        req=req,
    )


@router.get(
    path="/upload-process",
    status_code=200,
    response_model=schemas.files.FileUploadProcessResponse,
)
@utils.measure_time_spend
async def get_upload_process(
        h: utils.ANNOTATED_HEADERS,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.files.FileUploadProcessResponse:
    return await upload_files.get_upload_process(
        h=h,
    )
