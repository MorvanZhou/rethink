from typing import List

from fastapi import UploadFile

from retk import const
from retk.core.files.saver import saver, File


async def save_editor_upload_files(
        uid: str,
        files: List[UploadFile],
) -> dict:
    res = {
        "errFiles": [],
        "succMap": {},
        "code": const.CodeEnum.OK,
    }
    for file in files:
        filename = file.filename
        # validate MIME image type
        if not const.app.ValidUploadedFilePrefixEnum.is_valid(file.content_type):
            res["errFiles"].append(filename)
            res["code"] = const.CodeEnum.INVALID_FILE_TYPE
            continue

        # validate file type
        sep = filename.rsplit(".", 1)
        ext = f".{sep[-1]}" if len(sep) > 1 else ""
        if const.app.FileTypesEnum.get_type(ext) == const.app.FileTypesEnum.UNKNOWN:
            res["errFiles"].append(filename)
            res["code"] = const.CodeEnum.INVALID_FILE_TYPE
            continue

        # validate file size
        if file.size > const.settings.MAX_UPLOAD_FILE_SIZE:
            res["errFiles"].append(filename)
            res["code"] = const.CodeEnum.TOO_LARGE_FILE
            continue
        f = File(
            filename=filename,
            data=file.file,
        )
        if f.is_unknown_type():
            res["errFiles"].append(filename)
            res["code"] = const.CodeEnum.INVALID_FILE_TYPE
            continue

        url = await saver.save(
            uid=uid,
            file=f
        )
        if url == "":
            res["errFiles"].append(filename)
            res["code"] = const.CodeEnum.FILE_OPEN_ERROR
            continue
        res["succMap"][filename] = url
    return res
