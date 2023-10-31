from typing import List

from fastapi import Depends, APIRouter, UploadFile
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
