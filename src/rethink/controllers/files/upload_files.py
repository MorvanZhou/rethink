from typing import List

from fastapi import UploadFile

from rethink import const, core
from rethink.controllers import schemas
from rethink.controllers.utils import (
    Headers,
    datetime2str,
    is_allowed_mime_type,
)


async def upload_obsidian_files(
        h: Headers,
        files: List[UploadFile]
) -> schemas.files.FileUploadResponse:
    if h.code != const.Code.OK:
        return schemas.files.FileUploadResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            failedFilename="",
        )
    code = await core.files.upload_obsidian(uid=h.uid, zipped_files=files)

    return schemas.files.FileUploadResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
    )


async def upload_text_files(
        h: Headers,
        files: List[UploadFile]
) -> schemas.files.FileUploadResponse:
    if h.code != const.Code.OK:
        return schemas.files.FileUploadResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            failedFilename="",
        )
    code = await core.files.upload_text(uid=h.uid, files=files)
    return schemas.files.FileUploadResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        failedFilename="",
    )


async def get_upload_process(
        h: Headers,
) -> schemas.files.FileUploadProcessResponse:
    if h.code != const.Code.OK:
        return schemas.files.FileUploadProcessResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            process=0.,
            type="",
            startAt="",
            running=False,
            msg="",
        )
    doc = await core.files.get_upload_process(uid=h.uid)
    if doc is None:
        return schemas.files.FileUploadProcessResponse(
            code=const.Code.OK.value,
            message=const.get_msg_by_code(const.Code.OK, h.language),
            requestId=h.request_id,
            process=0.,
            type="",
            startAt="",
            running=False,
            msg="",
        )
    code = const.INT_CODE_MAP[doc["code"]]
    return schemas.files.FileUploadProcessResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        process=doc["process"],
        type=doc["type"],
        startAt=datetime2str(doc["startAt"]),
        running=doc["running"],
        msg=doc["msg"],
    )


async def upload_file_vditor(
        h: Headers,
        file: UploadFile,
) -> schemas.files.VditorFilesResponse:
    if h.code != const.Code.OK:
        return schemas.files.VditorFilesResponse(
            code=h.code.value,
            msg=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            data={},
        )
    res = await core.files.vditor_upload(uid=h.uid, files=[file])
    return schemas.files.VditorFilesResponse(
        code=res["code"].value,
        msg=const.get_msg_by_code(res["code"], h.language),
        requestId=h.request_id,
        data=schemas.files.VditorFilesResponse.Data(
            errFiles=res["errFiles"],
            succMap=res["succMap"],
        ),
    )


async def fetch_image_vditor(
        h: Headers,
        req: schemas.files.ImageVditorFetchRequest,
) -> schemas.files.VditorImagesResponse:
    if h.code != const.Code.OK:
        return schemas.files.VditorImagesResponse(
            code=h.code.value,
            msg=const.get_msg_by_code(h.code, h.language),
            data=schemas.files.VditorImagesResponse.Data(
                originalURL=req.url,
                url="",
            ),
        )
    if is_allowed_mime_type(req.url, ["image/svg+xml", "image/png", "image/jpeg", "image/gif"]):
        return schemas.files.VditorImagesResponse(
            code=const.Code.OK.value,
            msg=const.get_msg_by_code(const.Code.OK, h.language),
            data=schemas.files.VditorImagesResponse.Data(
                originalURL=req.url,
                url=req.url,
            ),
        )
    if len(req.url) > 2048:
        return schemas.files.VditorImagesResponse(
            code=const.Code.REQUEST_INPUT_ERROR.value,
            msg=const.get_msg_by_code(const.Code.REQUEST_INPUT_ERROR, h.language),
            data=schemas.files.VditorImagesResponse.Data(
                originalURL=req.url,
                url="",
            ),
        )
    new_url, code = await core.files.fetch_image_vditor(uid=h.uid, url=req.url)
    return schemas.files.VditorImagesResponse(
        code=code.value,
        msg=const.get_msg_by_code(code, h.language),
        data=schemas.files.VditorImagesResponse.Data(
            originalURL=req.url,
            url=new_url,
        ),
    )
