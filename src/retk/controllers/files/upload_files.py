from typing import List

from fastapi import UploadFile

from retk import const, core
from retk.controllers import schemas
from retk.controllers.utils import (
    AuthedUser,
    datetime2str,
    is_allowed_mime_type,
    maybe_raise_json_exception,
)


async def upload_obsidian_files(
        au: AuthedUser,
        files: List[UploadFile]
) -> schemas.RequestIdResponse:
    code = await core.files.upload_obsidian(au=au, zipped_files=files)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def upload_text_files(
        au: AuthedUser,
        files: List[UploadFile]
) -> schemas.RequestIdResponse:
    code = await core.files.upload_text(au=au, files=files)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def get_upload_process(
        au: AuthedUser,
) -> schemas.files.FileUploadProcessResponse:
    doc = await core.files.get_upload_process(uid=au.u.id)
    if doc is None:
        return schemas.files.FileUploadProcessResponse(
            code=const.Code.OK.value,
            msg=const.get_msg_by_code(const.Code.OK, au.language),
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
    return schemas.files.VditorFilesResponse(
        code=res["code"].value,
        msg=const.get_msg_by_code(res["code"], au.language),
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
        return schemas.files.VditorImagesResponse(
            requestId=au.request_id,
            data=schemas.files.VditorImagesResponse.Data(
                originalURL=req.url,
                url=req.url,
            ),
        )

    if len(req.url) > 2048:
        return maybe_raise_json_exception(
            au=au,
            code=const.Code.REQUEST_INPUT_ERROR,
        )

    new_url, code = await core.files.fetch_image_vditor(au=au, url=req.url)
    maybe_raise_json_exception(au=au, code=code)
    return schemas.files.VditorImagesResponse(
        requestId=au.request_id,
        data=schemas.files.VditorImagesResponse.Data(
            originalURL=req.url,
            url=new_url,
        ),
    )
