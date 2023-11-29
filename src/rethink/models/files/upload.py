import asyncio
import datetime
import io
import multiprocessing
import os
import time
import zipfile
from typing import List, Tuple, Optional

import httpx
import pymongo.errors
from bson import ObjectId
from bson.tz_util import utc
from fastapi import UploadFile
from starlette.datastructures import Headers

from rethink import const, models
from rethink.config import is_local_db
from rethink.logger import logger
from rethink.models.tps import ImportData
from . import file_ops

MAX_IMAGE_SIZE = 1024 * 1024 * 10  # 10 mb
RESIZE_IMG_THRESHOLD = 1024 * 256  # 256kb  # 1024 * 128  # 128 kb


async def update_process(
        uid: str,
        type_: str,
        process: int,
        start_at: datetime.datetime = None,
        running: bool = None,
        code: int = None,
) -> Tuple[Optional[ImportData], const.Code]:
    data = {"type": type_, "process": process}
    if start_at is not None:
        data["startAt"] = start_at
    if running is not None:
        data["running"] = running
    if code is not None:
        data["code"] = code
    if is_local_db():
        # local db not support find_one_and_update
        await models.database.COLL.import_data.update_one({"uid": uid}, {"$set": data})
        doc = await models.database.COLL.import_data.find_one({"uid": uid})
    else:
        doc = await models.database.COLL.import_data.find_one_and_update(
            {"uid": uid},
            {"$set": data}
        )
    if doc is None:
        return doc, const.Code.OPERATION_FAILED
    return doc, const.Code.OK


async def __set_running_false(
        uid: str,
        code: const.Code,
        msg: str = "",
) -> None:
    await models.database.COLL.import_data.update_one({"uid": uid}, {"$set": {
        "running": False,
        "msg": msg,
        "code": code.value,
    }})


def new_process_wrapper(func):
    async def try_new_process(
            *args, **kwargs
    ):
        if "new_process" in kwargs:
            is_new_process = kwargs["new_process"]
        else:
            is_new_process = args[0]
        if is_new_process:
            from rethink import models
            await models.database.set_client()
            await models.database.searcher().init()
            models.database.set_coll()
        try:
            await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"new process for uploading error: {e}")
            await __set_running_false(
                args[1],
                const.Code.OPERATION_FAILED,
                msg=f"new process for uploading error: {e}"
            )

        if is_new_process:
            try:
                await models.database.searcher().es.close()
            except AttributeError:
                pass

    return try_new_process


@new_process_wrapper
async def upload_obsidian_task(
        new_process: bool,
        uid: str,
        bytes_data: bytes,
        filename: str,
        doc: dict,
        max_file_size: int,
) -> None:
    t0 = time.time()
    if doc is None:
        doc: ImportData = {
            "_id": ObjectId(),
            "uid": uid,
            "process": 0,
            "type": "obsidian",
            "startAt": datetime.datetime.now(tz=utc),
            "running": True,
            "msg": "",
            "code": 0,
            "obsidian": {},
        }
        res = await models.database.COLL.import_data.insert_one(doc)
        if not res.acknowledged:
            await __set_running_false(
                uid,
                const.Code.OPERATION_FAILED,
                msg="insert new importData process failed",
            )
            return

    _, code = await update_process(
        uid=uid,
        type_="obsidian",
        process=0,
        start_at=datetime.datetime.now(tz=utc),
        running=True,
        code=0,
    )
    if code != const.Code.OK:
        await __set_running_false(
            uid,
            code,
            msg="update importData process failed",
        )
        return

    try:
        unzipped_files = file_ops.unzip_file(bytes_data)
    except zipfile.BadZipFile as e:
        await __set_running_false(
            uid,
            const.Code.INVALID_FILE_TYPE,
            msg=f"unzip failed: {e}"
        )
        logger.info(f"invalid file type: {filename}, uid: {uid}")
        return
    t1 = time.time()
    logger.info(f"obsidian upload, uid={uid}, unzip time: {t1 - t0:.2f}")

    filtered_files = {}
    existed_filename2nid = doc.get("obsidian", {}).copy()
    img_path_dict = {}
    img_name_dict = {}
    md_count = 0
    for filepath, data in unzipped_files.items():
        try:
            base_name, ext = filepath.rsplit(".", 1)
        except ValueError:
            continue
        valid_file = {"md", "txt"}
        valid_file.update(file_ops.VALID_IMG_EXT)
        if ext not in valid_file:
            continue
        if data["size"] > max_file_size:
            await __set_running_false(
                uid,
                const.Code.TOO_LARGE_FILE,
                msg=f"file size > {max_file_size}: {filepath}",
            )
            logger.info(f"too large file: {filepath}, uid: {uid}")
            return
        if ext in ["md", "txt"]:
            if len(filepath.split("/")) > 1:
                continue
            md_count += 1
            filtered_files[filepath] = data["file"]
        else:
            img_path_dict[filepath] = data["file"]
            img_name_dict[os.path.basename(filepath)] = data["file"]
    t2 = time.time()
    logger.info(f"obsidian upload, uid={uid}, filter time: {t2 - t1:.2f}")

    # add new md files with only title
    for i, (filepath, file_bytes) in enumerate(filtered_files.items()):
        base_name, ext = filepath.rsplit(".", 1)
        if base_name in existed_filename2nid:
            continue
        try:
            n, code = await models.node.add(
                uid=uid,
                md=base_name,
                type_=const.NodeType.MARKDOWN.value,
            )
        except pymongo.errors.DuplicateKeyError:
            logger.error(f"duplicate key: {filepath}, uid: {uid}")
            continue
        if code != const.Code.OK:
            await __set_running_false(
                uid,
                code,
                msg=f"new file insert failed: {filepath}",
            )
            logger.error(f"error: {code}, filepath: {filepath}, uid: {uid}")
            return
        existed_filename2nid[base_name] = n["id"]
        if i % 20 == 0:
            doc, code = await update_process(uid, "obsidian", int(i / md_count * 10))
            if code != const.Code.OK:
                await __set_running_false(
                    uid,
                    code,
                    msg="process updating failed",
                )
                logger.info(f"error: {code}, filepath: {filepath}, uid: {uid}")
                return
            if not doc["running"]:
                break
    t3 = time.time()
    logger.info(f"obsidian upload, uid={uid}, add new md time: {t3 - t2:.2f}")

    # update all files and update md files
    for i, (filepath, file_bytes) in enumerate(filtered_files.items()):
        base_name, ext = filepath.rsplit(".", 1)
        try:
            md = file_bytes.decode("utf-8")
        except (FileNotFoundError, OSError, UnicodeDecodeError) as e:
            logger.error(f"error: {e}. filepath: {filepath}")
            await __set_running_false(
                uid,
                const.Code.FILE_OPEN_ERROR,
                msg=f"file decode utf-8 failed, {e}: {filepath}",
            )
            logger.info(f"error: {const.Code.FILE_OPEN_ERROR}, filepath: {filepath}, uid: {uid}")
            return

        md = await file_ops.replace_inner_link_and_upload_image(
            uid=uid,
            md=md,
            exist_filename2nid=existed_filename2nid,
            img_path_dict=img_path_dict,
            img_name_dict=img_name_dict,
            resize_threshold=RESIZE_IMG_THRESHOLD,
        )
        md = base_name + "\n\n" + md
        nid = existed_filename2nid[base_name]
        n, code = await models.node.update(
            uid=uid,
            nid=nid,
            md=md,
            refresh_on_same_md=True,
        )
        if code == const.Code.NODE_NOT_EXIST:
            n, code = await models.node.add(
                uid=uid,
                md=md,
                type_=const.NodeType.MARKDOWN.value,
            )
            if code != const.Code.OK:
                await __set_running_false(
                    uid,
                    code,
                    msg=f"file insert failed: {filepath}",
                )
                logger.info(f"error: {code}, filepath: {filepath}, uid: {uid}")
                return
            existed_filename2nid[base_name] = n["id"]
        elif code != const.Code.OK:
            await __set_running_false(
                uid,
                code,
                msg=f"file updating failed: {filepath}",
            )
            logger.info(f"error: {code}, filepath: {filepath}, uid: {uid}")
            return
        if i % 20 == 0:
            doc, code = await update_process(uid, "obsidian", int(i / md_count * 40 + 10))
            if code != const.Code.OK:
                await __set_running_false(
                    uid,
                    code,
                    msg="uploading process update failed",
                )
                logger.info(f"error: {code}, filepath: {filepath}, uid: {uid}")
                return
            if not doc["running"]:
                break
    t4 = time.time()
    logger.info(f"obsidian upload, uid={uid}, update all files time: {t4 - t3:.2f}")

    # update for old obsidian files
    count = 0
    for base_name, nid in doc["obsidian"].items():
        if base_name not in existed_filename2nid:
            n, code = await models.node.get(uid=uid, nid=nid)
            if code != const.Code.OK:
                continue
            n, code = await models.node.update(
                uid=uid,
                nid=nid,
                md=n["md"],
                refresh_on_same_md=True,
            )
            if code != const.Code.OK:
                continue
        if count % 20 == 0:
            doc, code = await update_process(uid, "obsidian", int(count / len(doc["obsidian"]) * 50 + 50))
            if code != const.Code.OK:
                await __set_running_false(
                    uid,
                    code,
                    msg="uploading process update failed",
                )
                logger.info(f"error: {code}, uid: {uid}")
                return
            if not doc["running"]:
                break

        count += 1

    t5 = time.time()
    logger.info(f"obsidian upload, uid={uid}, update for old obsidian files time: {t5 - t4:.2f}")

    await models.database.COLL.import_data.update_one(
        {"uid": uid},
        {"$set": {
            "obsidian": existed_filename2nid,
            "running": False,
            "msg": "",
            "code": 0,
            "process": 100,
        }})


def async_upload_obsidian(*args, **kwargs):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()

    loop.run_until_complete(upload_obsidian_task(*args, **kwargs))
    loop.close()


async def upload_obsidian(uid: str, zipped_files: List[UploadFile]) -> const.Code:
    max_file_count = 1
    max_file_size = 1024 * 1024 * 200  # 200 mb

    doc = await models.database.COLL.import_data.find_one({"uid": uid})
    if doc and doc["running"]:
        return const.Code.IMPORT_PROCESS_NOT_FINISHED

    # check file type and size and number
    if len(zipped_files) > max_file_count:
        await __set_running_false(
            uid,
            const.Code.TOO_MANY_FILES,
            msg=f"too many files: {len(zipped_files)} > {max_file_count} (max file count)",
        )
        return const.Code.TOO_MANY_FILES

    zipped_file = zipped_files[0]
    if not zipped_file.filename.endswith(".zip"):
        await __set_running_false(
            uid,
            const.Code.INVALID_FILE_TYPE,
            msg=f"invalid file type: {zipped_file.filename}",
        )
        return const.Code.INVALID_FILE_TYPE
    if zipped_file.content_type not in ["application/zip", "application/octet-stream", "application/x-zip-compressed"]:
        await __set_running_false(
            uid,
            const.Code.INVALID_FILE_TYPE,
            msg=f"invalid file type: {zipped_file.content_type}",
        )
        return const.Code.INVALID_FILE_TYPE

    if is_local_db():
        # local db not support find_one_and_update
        await upload_obsidian_task(
            new_process=False,
            uid=uid,
            bytes_data=zipped_file.file.read(),
            filename=zipped_file.filename,
            doc=doc,
            max_file_size=max_file_size,

        )
    else:
        ctx = multiprocessing.get_context('spawn')
        p = ctx.Process(
            target=async_upload_obsidian,
            args=(True, uid, zipped_file.file.read(), zipped_file.filename, doc, max_file_size),
            daemon=True,
        )
        p.start()
    return const.Code.OK


@new_process_wrapper
async def update_text_task(
        new_process: bool,
        uid: str,
        files: List[dict],
        max_file_size: int,
):
    doc = await models.database.COLL.import_data.find_one({"uid": uid})
    if doc is None:
        doc: ImportData = {
            "_id": ObjectId(),
            "uid": uid,
            "process": 0,
            "type": "text",
            "startAt": datetime.datetime.now(tz=utc),
            "running": True,
            "msg": "",
            "code": 0,
            "obsidian": {},
        }
        res = await models.database.COLL.import_data.insert_one(doc)
        if not res.acknowledged:
            await __set_running_false(
                uid,
                const.Code.OPERATION_FAILED,
                msg="insert new importData process failed",
            )
            return const.Code.OPERATION_FAILED

    _, code = await update_process(
        uid,
        "text",
        0,
        start_at=datetime.datetime.now(tz=utc),
        running=True,
        code=0,
    )
    if code != const.Code.OK:
        await __set_running_false(
            uid,
            code,
            msg="update importData process failed",
        )
        return

    for file in files:
        if not file["filename"].endswith(".md") and not file["filename"].endswith(".txt"):
            await __set_running_false(
                uid,
                const.Code.INVALID_FILE_TYPE,
                msg=f"invalid file type: {file['filename']}",
            )
            return
        if file["size"] > max_file_size:
            await __set_running_false(
                uid,
                const.Code.TOO_LARGE_FILE,
                msg=f"file size: {file['size']} > {max_file_size} (max file size): {file['filename']}",
            )
            return

    for i, file in enumerate(files):
        try:
            md = file["content"].decode("utf-8")
        except (FileNotFoundError, OSError) as e:
            logger.error(f"error: {e}. filepath: {file['filename']}")
            await __set_running_false(
                uid,
                const.Code.FILE_OPEN_ERROR,
                msg=f"file decode utf-8 failed, {e}: {file['filename']}",
            )
            return
        title = file["filename"].rsplit(".", 1)[0]
        md = title + "\n\n" + md
        try:
            n, code = await models.node.add(
                uid=uid,
                md=md,
                type_=const.NodeType.MARKDOWN.value,
            )
        except pymongo.errors.DuplicateKeyError:
            continue
        except Exception as e:
            logger.error(f"error: {e}. filepath: {file['filename']}")
            await __set_running_false(
                uid,
                const.Code.FILE_OPEN_ERROR,
                msg=f"file decode utf-8 failed, {e}: {file['filename']}",
            )
            return
        if code != const.Code.OK:
            await __set_running_false(
                uid,
                code,
                msg=f"file insert failed: {file['filename']}",
            )
            return
        if i % 20 == 0:
            doc, code = await update_process(uid, "text", int(i / len(files) * 100))
            if code != const.Code.OK:
                await __set_running_false(
                    uid,
                    code,
                    msg="uploading process update failed",
                )
                return
            if not doc["running"]:
                break
    resp = await models.database.COLL.import_data.update_one(
        {"uid": uid},
        {"$set": {
            "running": False,
            "process": 100,
            "code": 0,
            "msg": "",
        }})

    if resp.modified_count != 1:
        await __set_running_false(
            uid,
            const.Code.OPERATION_FAILED,
            msg="uploading importData process failed",
        )


def async_upload_text_task(*args, **kwargs):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()

    loop.run_until_complete(update_text_task(*args, **kwargs))
    loop.close()


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
        await update_text_task(
            new_process=False,
            uid=uid,
            files=file_list,
            max_file_size=max_file_size,
        )
    else:
        ctx = multiprocessing.get_context('spawn')
        p = ctx.Process(
            target=async_upload_text_task,
            args=(True, uid, file_list, max_file_size),
            daemon=True,
        )
        p.start()
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
        resize_threshold=RESIZE_IMG_THRESHOLD,
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
        resize_threshold=RESIZE_IMG_THRESHOLD,
    )
    if len(res["errFiles"]) > 0:
        return "", const.Code.FILE_OPEN_ERROR
    return res["succMap"][file.filename], const.Code.OK
