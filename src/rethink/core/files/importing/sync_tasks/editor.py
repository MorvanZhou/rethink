from typing import List

from fastapi import UploadFile

from rethink import const
from rethink.core.files.saver import saver, File


async def save_editor_upload_files(
        uid: str,
        files: List[UploadFile],
        max_image_size: int,
) -> dict:
    res = {
        "errFiles": [],
        "succMap": {},
        "code": const.Code.OK,
    }
    for file in files:
        filename = file.filename
        # validate MIME image type
        if not file.content_type.startswith("image/"):
            res["errFiles"].append(filename)
            continue
        if file.size > max_image_size:
            res["errFiles"].append(filename)
            continue
        url = await saver.save(
            uid=uid,
            file=File(
                filename=filename,
                data=file.file,
            )
        )
        if url == "":
            res["errFiles"].append(filename)
            continue
        res["succMap"][filename] = url
    return res
