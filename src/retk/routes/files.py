from typing import List, Optional

from fastapi import APIRouter, UploadFile, Request

from retk.controllers import schemas
from retk.controllers.files import upload_files
from retk.routes import utils

router = APIRouter(
    prefix="/api/files",
    tags=["files"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/obsidian",
    status_code=202,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def upload_obsidian_files(
        au: utils.ANNOTATED_AUTHED_USER,
        files: List[UploadFile],
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await upload_files.upload_obsidian_files(
        au=au,
        files=files,
    )


@router.post(
    path="/text",
    status_code=202,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def upload_text_files(
        au: utils.ANNOTATED_AUTHED_USER,
        files: List[UploadFile],
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await upload_files.upload_text_files(
        au=au,
        files=files,
    )


@router.post(
    path="/vditor",
    status_code=200,
    response_model=schemas.files.VditorFilesResponse,
)
@utils.measure_time_spend
async def vditor_upload(
        au: utils.ANNOTATED_AUTHED_USER,
        req: Request,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.files.VditorFilesResponse:
    form = await req.form()
    file = form.get("file[]")
    return await upload_files.upload_file_vditor(
        au=au,
        file=file,
    )


@router.post(
    path="/vditor/images",
    status_code=200,
    response_model=schemas.files.VditorImagesResponse,
)
@utils.measure_time_spend
async def vditor_fetch_image(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.files.ImageVditorFetchRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.files.VditorImagesResponse:
    return await upload_files.fetch_image_vditor(
        au=au,
        req=req,
    )


@router.get(
    path="/upload-process",
    status_code=200,
    response_model=schemas.files.FileUploadProcessResponse,
)
@utils.measure_time_spend
async def get_upload_process(
        au: utils.ANNOTATED_AUTHED_USER,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.files.FileUploadProcessResponse:
    return await upload_files.get_upload_process(
        au=au,
    )
