from typing import List

from fastapi import UploadFile

from rethink import const, models
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode
from ..utils import datetime2str


def upload_obsidian_files(
        td: TokenDecode,
        files: List[UploadFile]
) -> schemas.files.FileUploadResponse:
    if td.code != const.Code.OK:
        return schemas.files.FileUploadResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId="",
            failedFilename="",
        )
    problem_file, code = models.files.upload_obsidian(uid=td.uid, files=files)
    if code != const.Code.OK:
        return schemas.files.FileUploadResponse(
            code=code.value,
            message=const.get_msg_by_code(code, td.language),
            requestId="",
            failedFilename=problem_file,
        )
    return schemas.files.FileUploadResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, td.language),
        requestId="",
        failedFilename="",
    )


def upload_text_files(
        td: TokenDecode,
        files: List[UploadFile]
) -> schemas.files.FileUploadResponse:
    if td.code != const.Code.OK:
        return schemas.files.FileUploadResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId="",
            failedFilename="",
        )
    problem_file, code = models.files.upload_text(uid=td.uid, files=files)
    if code != const.Code.OK:
        return schemas.files.FileUploadResponse(
            code=code.value,
            message=const.get_msg_by_code(code, td.language),
            requestId="",
            failedFilename=problem_file,
        )
    return schemas.files.FileUploadResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, td.language),
        requestId="",
        failedFilename="",
    )


def get_upload_process(
        td: TokenDecode,
        rid: str,
) -> schemas.files.FileUploadProcessResponse:
    if td.code != const.Code.OK:
        return schemas.files.FileUploadProcessResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=rid,
            process=0.,
            type="",
            startAt="",
        )
    process, ty, start_at, running = models.files.get_upload_process(uid=td.uid)
    return schemas.files.FileUploadProcessResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, td.language),
        requestId=rid,
        process=process,
        type=ty,
        startAt=datetime2str(start_at),
        running=running,
    )


def upload_image_vditor(
        td: TokenDecode,
        file: UploadFile,
) -> schemas.files.ImageVditorUploadResponse:
    if td.code != const.Code.OK:
        return schemas.files.ImageVditorUploadResponse(
            code=td.code.value,
            msg=const.get_msg_by_code(td.code, td.language),
            data={},
        )
    res = models.files.upload_image_vditor(uid=td.uid, files=[file])
    return schemas.files.ImageVditorUploadResponse(
        code=const.Code.OK.value,
        msg=const.get_msg_by_code(const.Code.OK, td.language),
        data=res,
    )


def fetch_image_vditor(
        td: TokenDecode,
        req: schemas.files.ImageVditorFetchRequest,
) -> schemas.files.ImageVditorFetchResponse:
    if td.code != const.Code.OK:
        return schemas.files.ImageVditorFetchResponse(
            code=td.code.value,
            msg=const.get_msg_by_code(td.code, td.language),
            data={},
        )
    new_url, code = models.files.fetch_image_vditor(uid=td.uid, url=req.url)
    return schemas.files.ImageVditorFetchResponse(
        code=const.Code.OK.value,
        msg=const.get_msg_by_code(const.Code.OK, td.language),
        data=schemas.files.ImageVditorFetchResponse.Data(
            originalURL=req.url,
            url=new_url,
        ),
    )
