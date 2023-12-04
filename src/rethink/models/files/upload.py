import datetime
import io
from typing import List, Tuple, Optional

import httpx
from bson.tz_util import utc
from fastapi import UploadFile
from starlette.datastructures import Headers

from rethink import const, models
from rethink.config import is_local_db
from rethink.logger import logger
from . import file_ops, queuing_upload

MAX_IMAGE_SIZE = 1024 * 1024 * 10  # 10 mb
QUEUE_INITED = False


async def upload_obsidian(uid: str, zipped_files: List[UploadFile]) -> const.Code:
    max_file_count = 1
    max_file_size = 1024 * 1024 * 200  # 200 mb

    if len(zipped_files) > max_file_count:
        return const.Code.TOO_MANY_FILES

    zipped_file = zipped_files[0]
    if not zipped_file.filename.endswith(".zip"):
        return const.Code.INVALID_FILE_TYPE

    if zipped_file.content_type not in ["application/zip", "application/octet-stream", "application/x-zip-compressed"]:
        return const.Code.INVALID_FILE_TYPE

    bytes_data = zipped_file.file.read()
    filename = zipped_file.filename

    if is_local_db():
        # local db not support find_one_and_update
        await queuing_upload.upload_obsidian_task(
            bytes_data=bytes_data,
            filename=filename,
            max_file_size=max_file_size,
            uid=uid,
        )
    else:
        global QUEUE_INITED
        if not QUEUE_INITED:
            queuing_upload.init()
            QUEUE_INITED = True
        queuing_upload.QUEUE.put_nowait({
            "task": "obsidian",
            "bytes_data": bytes_data,
            "filename": filename,
            "max_file_size": max_file_size,
            "uid": uid,
        })
    return const.Code.OK


async def upload_text(uid: str, files: List[UploadFile]) -> const.Code:
    max_file_count = 200
    max_file_size = 1024 * 512  # 512 kb

    doc = await models.database.COLL.import_data.find_one({"uid": uid})
    if doc is not None and doc["running"]:
        return const.Code.IMPORT_PROCESS_NOT_FINISHED

    if len(files) > max_file_count:
        return const.Code.TOO_MANY_FILES

    file_list = [{
        "filename": file.filename,
        "content": file.file.read(),
        "size": file.size,
    } for file in files]

    if is_local_db():
        # local db not support find_one_and_update
        await queuing_upload.update_text_task(
            files=file_list,
            max_file_size=max_file_size,
            uid=uid,
        )
    else:
        global QUEUE_INITED
        if not QUEUE_INITED:
            queuing_upload.init()
            QUEUE_INITED = True
        queuing_upload.QUEUE.put_nowait({
            "task": "md",
            "files": file_list,
            "max_file_size": max_file_size,
            "uid": uid,
        })
    return const.Code.OK


async def get_upload_process(uid: str) -> Optional[dict]:
    timeout_minus = 5
    doc = await models.database.COLL.import_data.find_one({"uid": uid})
    if doc is None:
        return None
    now = datetime.datetime.now(tz=utc)

    # upload timeout
    if doc["running"] and \
            now.replace(tzinfo=None) - doc["startAt"].replace(tzinfo=None) \
            > datetime.timedelta(minutes=timeout_minus):
        doc["running"] = False
        await models.database.COLL.import_data.update_one(
            {"uid": uid},
            {"$set": {
                "running": False,
                "code": const.Code.UPLOAD_TASK_TIMEOUT.value,
                "msg": f"Timeout, upload not finish in {timeout_minus} mins",
            }},
        )
    return doc


async def upload_image_vditor(uid: str, files: List[UploadFile]) -> dict:
    res = {
        "errFiles": [],
        "succMap": {},
        "code": const.Code.OK,
    }
    u, code = await models.user.get(uid=uid)
    if code != const.Code.OK:
        res["errFiles"] = [file.filename for file in files]
        res["code"] = code
        return res
    if await models.user.user_space_not_enough(u=u):
        res["errFiles"] = [file.filename for file in files]
        res["code"] = const.Code.USER_SPACE_NOT_ENOUGH
        return res

    return await file_ops.save_upload_files(
        uid=uid,
        files=files,
        max_image_size=MAX_IMAGE_SIZE,
        resize_threshold=queuing_upload.RESIZE_IMG_THRESHOLD,
    )


async def fetch_image_vditor(uid: str, url: str) -> Tuple[str, const.Code]:
    u, code = await models.user.get(uid=uid)
    if code != const.Code.OK:
        return "", code
    if await models.user.user_space_not_enough(u=u):
        return "", const.Code.USER_SPACE_NOT_ENOUGH
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url=url,
                headers=models.utils.ASYNC_CLIENT_HEADERS,
                timeout=5.
            )
        except (
                httpx.ConnectTimeout,
                RuntimeError,
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.HTTPError
        ) as e:
            logger.info(f"failed to get {url}: {e}")
            return "", const.Code.FILE_OPEN_ERROR
        if response.status_code != 200:
            return "", const.Code.FILE_OPEN_ERROR

        content = response.content

        file = UploadFile(
            filename=url.split("/")[-1],
            file=io.BytesIO(content),
            headers=Headers(response.headers),
            size=len(content)
        )

    res = await file_ops.save_upload_files(
        uid=uid,
        files=[file],
        max_image_size=MAX_IMAGE_SIZE,
        resize_threshold=queuing_upload.RESIZE_IMG_THRESHOLD,
    )
    if len(res["errFiles"]) > 0:
        return "", const.Code.FILE_OPEN_ERROR
    return res["succMap"][file.filename], const.Code.OK
