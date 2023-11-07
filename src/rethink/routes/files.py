from typing import List

from fastapi import Depends, APIRouter, UploadFile, Request
from typing_extensions import Annotated

from rethink.controllers import schemas
from rethink.controllers.auth import token2uid
from rethink.controllers.files import upload_files
from rethink.controllers.utils import TokenDecode
from rethink.routes.utils import measure_time_spend

router = APIRouter(
    prefix="/api",
    tags=["files"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/files/obsidian",
    response_model=schemas.files.FileUploadResponse,
)
@measure_time_spend
async def upload_obsidian_files(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        files: List[UploadFile],
) -> schemas.files.FileUploadResponse:
    return upload_files.upload_obsidian_files(
        td=token_decode,
        files=files,
    )


@router.post(
    path="/files/text",
    response_model=schemas.files.FileUploadResponse,
)
@measure_time_spend
async def upload_obsidian_files(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        files: List[UploadFile],
) -> schemas.files.FileUploadResponse:
    return upload_files.upload_text_files(
        td=token_decode,
        files=files,
    )


@router.get(
    path="/files/uploadProcess",
    response_model=schemas.files.FileUploadProcessResponse,
)
@measure_time_spend
async def get_upload_process(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        rid: str,
) -> schemas.files.FileUploadProcessResponse:
    return upload_files.get_upload_process(
        td=token_decode,
        rid=rid,
    )


@router.post(
    path="/files/imageUploadVditor",
    response_model=schemas.files.ImageVditorUploadResponse,
)
@measure_time_spend
async def upload_image_vditor(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        req: Request,
) -> schemas.files.ImageVditorUploadResponse:
    form = await req.form()
    file = form.get("file[]")
    return upload_files.upload_image_vditor(
        td=token_decode,
        file=file,
    )


@router.post(
    path="/files/imageFetchVditor",
    response_model=schemas.files.ImageVditorFetchResponse,
)
@measure_time_spend
async def fetch_image_vditor(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        req: schemas.files.ImageVditorFetchRequest,
) -> schemas.files.ImageVditorFetchResponse:
    return upload_files.fetch_image_vditor(
        td=token_decode,
        req=req,
    )
