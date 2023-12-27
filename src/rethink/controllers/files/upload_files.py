from typing import List

from fastapi import UploadFile

from rethink import const, models
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode
from ..utils import datetime2str, is_allowed_mime_type


async def upload_obsidian_files(
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
    code = await models.files.upload_obsidian(uid=td.uid, zipped_files=files)

    return schemas.files.FileUploadResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId="",
    )


async def upload_text_files(
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
    code = await models.files.upload_text(uid=td.uid, files=files)
    return schemas.files.FileUploadResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId="",
        failedFilename="",
    )


async def get_upload_process(
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
            running=False,
            msg="",
        )
    doc = await models.files.get_upload_process(uid=td.uid)
    if doc is None:
        return schemas.files.FileUploadProcessResponse(
            code=const.Code.OK.value,
            message=const.get_msg_by_code(const.Code.OK, td.language),
            requestId=rid,
            process=0.,
            type="",
            startAt="",
            running=False,
            msg="",
        )
    code = const.INT_CODE_MAP[doc["code"]]
    return schemas.files.FileUploadProcessResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=rid,
        process=doc["process"],
        type=doc["type"],
        startAt=datetime2str(doc["startAt"]),
        running=doc["running"],
        msg=doc["msg"],
    )


async def upload_image_vditor(
        td: TokenDecode,
        file: UploadFile,
) -> schemas.files.ImageVditorUploadResponse:
    if td.code != const.Code.OK:
        return schemas.files.ImageVditorUploadResponse(
            code=td.code.value,
            msg=const.get_msg_by_code(td.code, td.language),
            data={},
        )
    res = await models.files.upload_image_vditor(uid=td.uid, files=[file])
    return schemas.files.ImageVditorUploadResponse(
        code=const.Code.OK.value,
        msg=const.get_msg_by_code(const.Code.OK, td.language),
        data=res,
    )


async def fetch_image_vditor(
        td: TokenDecode,
        req: schemas.files.ImageVditorFetchRequest,
) -> schemas.files.ImageVditorFetchResponse:
    if td.code != const.Code.OK:
        return schemas.files.ImageVditorFetchResponse(
            code=td.code.value,
            msg=const.get_msg_by_code(td.code, td.language),
            data=schemas.files.ImageVditorFetchResponse.Data(
                originalURL=req.url,
                url="",
            ),
        )
    if is_allowed_mime_type(req.url, ["image/svg+xml", "image/png", "image/jpeg", "image/gif"]):
        return schemas.files.ImageVditorFetchResponse(
            code=const.Code.OK.value,
            msg=const.get_msg_by_code(const.Code.OK, td.language),
            data=schemas.files.ImageVditorFetchResponse.Data(
                originalURL=req.url,
                url=req.url,
            ),
        )
    if len(req.url) > 2048:
        return schemas.files.ImageVditorFetchResponse(
            code=const.Code.REQUEST_INPUT_ERROR.value,
            msg=const.get_msg_by_code(const.Code.REQUEST_INPUT_ERROR, td.language),
            data=schemas.files.ImageVditorFetchResponse.Data(
                originalURL=req.url,
                url="",
            ),
        )
    new_url, code = await models.files.fetch_image_vditor(uid=td.uid, url=req.url)
    return schemas.files.ImageVditorFetchResponse(
        code=code.value,
        msg=const.get_msg_by_code(code, td.language),
        data=schemas.files.ImageVditorFetchResponse.Data(
            originalURL=req.url,
            url=new_url,
        ),
    )
