from typing import List
from urllib.parse import urlparse

from fastapi import UploadFile

from retk import const, core
from retk.config import get_settings
from retk.controllers import schemas
from retk.controllers.utils import (
    AuthedUser,
    is_allowed_mime_type,
    maybe_raise_json_exception,
)
from retk.utils import datetime2str


async def upload_obsidian_files(
        au: AuthedUser,
        files: List[UploadFile]
) -> schemas.RequestIdResponse:
    code = await core.files.upload_obsidian(au=au, zipped_files=files)
    maybe_raise_json_exception(au=au, code=code)
    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.NODE_DATA_IMPORT,
        remark="obsidian",
    )
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def upload_text_files(
        au: AuthedUser,
        files: List[UploadFile]
) -> schemas.RequestIdResponse:
    code = await core.files.upload_text(au=au, files=files)
    maybe_raise_json_exception(au=au, code=code)

    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.NODE_DATA_IMPORT,
        remark="text",
    )
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def get_upload_process(
        au: AuthedUser,
) -> schemas.files.FileUploadProcessResponse:
    doc = await core.files.get_upload_process(uid=au.u.id)
    if doc is None:
        code = const.CodeEnum.OK
        return schemas.files.FileUploadProcessResponse(
            code=code.value,
            msg=const.get_msg_by_code(code, au.language),
            requestId=au.request_id,
            process=0.,
            type="",
            startAt="",
            running=False,
        )

    return schemas.files.FileUploadProcessResponse(
        code=doc["code"],
        msg=doc["msg"],
        requestId=au.request_id,
        process=doc["process"],
        type=doc["type"],
        startAt=datetime2str(doc["startAt"]),
        running=doc["running"],
    )


async def upload_file_vditor(
        au: AuthedUser,
        file: UploadFile,
) -> schemas.files.VditorFilesResponse:
    res = await core.files.vditor_upload(au=au, files=[file])
    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.NODE_FILE_UPLOAD,
        remark="vditorFile",
    )
    return schemas.files.VditorFilesResponse(
        msg=const.get_msg_by_code(res["code"], au.language),
        code=res["code"].value,
        requestId=au.request_id,
        data=schemas.files.VditorFilesResponse.Data(
            errFiles=res["errFiles"],
            succMap=res["succMap"],
        ),
    )


async def fetch_image_vditor(
        au: AuthedUser,
        req: schemas.files.ImageVditorFetchRequest,
) -> schemas.files.VditorImagesResponse:
    if is_allowed_mime_type(req.url, ["image/svg+xml", "image/png", "image/jpeg", "image/gif"]):
        code = const.CodeEnum.OK
        return schemas.files.VditorImagesResponse(
            msg=const.get_msg_by_code(code, au.language),
            code=code.value,
            requestId=au.request_id,
            data=schemas.files.VditorImagesResponse.Data(
                originalURL=req.url,
                url=req.url,
            ),
        )
    domain = urlparse(req.url).netloc
    if get_settings().COS_DOMAIN != "" and domain == get_settings().COS_DOMAIN:
        new_url, code = req.url, const.CodeEnum.OK
    else:
        if len(req.url) <= 2048:
            new_url, code = await core.files.fetch_image_vditor(au=au, url=req.url)
        else:
            new_url, code = "", const.CodeEnum.URL_TOO_LONG
    maybe_raise_json_exception(au=au, code=code)

    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.NODE_FILE_UPLOAD,
        remark="vditorImage",
    )
    return schemas.files.VditorImagesResponse(
        msg=const.get_msg_by_code(code, au.language),
        code=code.value,
        requestId=au.request_id,
        data=schemas.files.VditorImagesResponse.Data(
            originalURL=req.url,
            url=new_url,
        ),
    )
