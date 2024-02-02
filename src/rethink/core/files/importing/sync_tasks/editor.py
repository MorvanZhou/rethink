from typing import List

from fastapi import UploadFile

from rethink import const
from rethink.core.files.saver import saver, File


async def save_editor_upload_files(
        uid: str,
        files: List[UploadFile],
) -> dict:
    res = {
        "errFiles": [],
        "succMap": {},
        "code": const.Code.OK,
    }
    for file in files:
        filename = file.filename
        # validate MIME image type
        if not const.ValidUploadedFilePrefix.is_valid(file.content_type):
            res["errFiles"].append(filename)
            res["code"] = const.Code.INVALID_FILE_TYPE
            continue

        # validate file type
        sep = filename.rsplit(".", 1)
        ext = f".{sep[-1]}" if len(sep) > 1 else ""
        if const.FileTypes.get_type(ext) == const.FileTypes.UNKNOWN:
            res["errFiles"].append(filename)
            res["code"] = const.Code.INVALID_FILE_TYPE
            continue

        # validate file size
        if file.size > const.MAX_UPLOAD_FILE_SIZE:
            res["errFiles"].append(filename)
            res["code"] = const.Code.TOO_LARGE_FILE
            continue
        f = File(
            filename=filename,
            data=file.file,
        )
        if f.is_unknown_type():
            res["errFiles"].append(filename)
            res["code"] = const.Code.INVALID_FILE_TYPE
            continue

        url = await saver.save(
            uid=uid,
            file=f
        )
        if url == "":
            res["errFiles"].append(filename)
            res["code"] = const.Code.FILE_OPEN_ERROR
            continue
        res["succMap"][filename] = url
    return res
