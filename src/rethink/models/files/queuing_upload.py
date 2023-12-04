import asyncio
import datetime
import multiprocessing
import os
import time
import zipfile
from typing import List, Optional, Tuple

import pymongo.errors
from bson import ObjectId
from bson.tz_util import utc

from rethink import const, models, config
from rethink.logger import logger
from rethink.models.files import file_ops
from rethink.models.tps import ImportData

RESIZE_IMG_THRESHOLD = 1024 * 256  # 256kb  # 1024 * 128  # 128 kb

ctx = multiprocessing.get_context('spawn')
QUEUE = ctx.Queue()


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
    if config.is_local_db():
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


async def import_set_modules():
    from rethink import models

    await models.database.set_client()
    await models.database.searcher().init()
    models.database.set_coll()


async def __check_last_task_finished(uid: str, type_: str) -> Tuple[Optional[ImportData], bool]:
    doc = await models.database.COLL.import_data.find_one({"uid": uid})
    if doc and doc["running"]:
        await __set_running_false(
            uid=uid,
            code=const.Code.IMPORT_PROCESS_NOT_FINISHED,
            msg="last importData process not finished, please try again later",
        )
        return None, False

    if doc is None:
        doc: ImportData = {
            "_id": ObjectId(),
            "uid": uid,
            "process": 0,
            "type": type_,
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
            return doc, False
    else:
        doc, code = await update_process(
            uid=uid,
            type_=type_,
            process=0,
            start_at=datetime.datetime.now(tz=utc),
            running=True,
            code=0,
        )
        if code != const.Code.OK:
            await __set_running_false(
                uid=uid,
                code=code,
                msg="update importData process failed",
            )
            return doc, False
    return doc, True


async def __finish_task(uid: str, obsidian=None):
    resp = await models.database.COLL.import_data.update_one(
        {"uid": uid},
        {"$set": {
            "obsidian": obsidian or {},
            "running": False,
            "process": 100,
            "code": 0,
            "msg": "done",
        }})

    if resp.modified_count != 1:
        await __set_running_false(
            uid=uid,
            code=const.Code.OPERATION_FAILED,
            msg="uploading importData process failed",
        )


async def update_text_task(
        files: List[dict],
        max_file_size: int,
        uid: str,
):
    type_ = "md"
    await import_set_modules()

    doc, finished = await __check_last_task_finished(uid=uid, type_=type_)
    if not finished:
        return

    for file in files:
        if not file["filename"].endswith(".md") and not file["filename"].endswith(".txt"):
            await __set_running_false(
                uid=uid,
                code=const.Code.INVALID_FILE_TYPE,
                msg=f"invalid file type: {file['filename']}",
            )
            return
        if file["size"] > max_file_size:
            await __set_running_false(
                uid=uid,
                code=const.Code.TOO_LARGE_FILE,
                msg=f"file size: {file['size']} > {max_file_size} (max file size): {file['filename']}",
            )
            return

    for i, file in enumerate(files):
        try:
            md = file["content"].decode("utf-8")
        except (FileNotFoundError, OSError) as e:
            logger.error(f"error: {e}. filepath: {file['filename']}")
            await __set_running_false(
                uid=uid,
                code=const.Code.FILE_OPEN_ERROR,
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
                uid=uid,
                code=const.Code.FILE_OPEN_ERROR,
                msg=f"file decode utf-8 failed, {e}: {file['filename']}",
            )
            return
        if code != const.Code.OK:
            await __set_running_false(
                uid=uid,
                code=code,
                msg=f"file insert failed: {file['filename']}",
            )
            return
        if i % 20 == 0:
            doc, code = await update_process(uid=uid, type_=type_, process=int(i / len(files) * 100))
            if code != const.Code.OK:
                await __set_running_false(
                    uid=uid,
                    code=code,
                    msg="uploading process update failed",
                )
                return
            if not doc["running"]:
                break

    await __finish_task(uid=uid)


async def upload_obsidian_task(
        bytes_data: bytes,
        filename: str,
        max_file_size: int,
        uid: str,
) -> None:
    type_ = "obsidian"
    await import_set_modules()

    doc, finished = await __check_last_task_finished(uid=uid, type_=type_)
    if not finished:
        return

    t0 = time.time()
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
            doc, code = await update_process(uid=uid, type_=type_, process=int(i / md_count * 10))
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
            doc, code = await update_process(uid=uid, type_=type_, process=int(i / md_count * 40 + 10))
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
            doc, code = await update_process(uid=uid, type_=type_, process=int(count / len(doc["obsidian"]) * 50 + 50))
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

    await __finish_task(uid=uid, obsidian=existed_filename2nid)


def async_task(queue: multiprocessing.Queue):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    while True:
        item = queue.get()
        task = item.pop("task")
        if task == "md":
            func = update_text_task
        elif task == "obsidian":
            func = upload_obsidian_task
        else:
            logger.error(f"unknown task: {task}")
            continue
        try:
            loop.run_until_complete(func(**item))
        except Exception as e:
            logger.error(f"async task error: {e}")
    loop.close()


def init():
    p = ctx.Process(
        target=async_task,
        args=(QUEUE,),
        daemon=True,
    )
    p.start()
