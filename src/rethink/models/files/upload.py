import datetime
import io
import os
import threading
from typing import List, Tuple, Optional

import pymongo.errors
import requests
from bson import ObjectId
from bson.tz_util import utc
from fastapi import UploadFile
from starlette.datastructures import Headers

from rethink import const, models
from rethink.config import is_local_db
from rethink.logger import logger
from rethink.models import utils
from rethink.models.database import COLL
from rethink.models.tps import ImportData
from .unzip import unzip_file

MAX_IMAGE_SIZE = 1024 * 1024 * 10  # 10 mb
MIN_IMAGE_SIZE = 1024 * 128  # 128 kb


def update_process(
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
        COLL.import_data.update_one({"uid": uid}, {"$set": data})
        doc = COLL.import_data.find_one({"uid": uid})
    else:
        doc = COLL.import_data.find_one_and_update({"uid": uid}, {
            "$set": data})
    if doc is None:
        return doc, const.Code.OPERATION_FAILED
    return doc, const.Code.OK


def __set_running_false(uid: str, code: const.Code, problem_files: List[str] = None) -> None:
    COLL.import_data.update_one({"uid": uid}, {"$set": {
        "running": False,
        "problemFiles": problem_files if problem_files is not None else [],
        "code": code.value,
    }})


def upload_obsidian_thread(
        uid: str,
        zipped_file: UploadFile,
        doc: dict,
        max_file_size: int,
) -> None:
    unzipped_files = unzip_file(zipped_file.file.read())
    filtered_files = {}
    existed_filename2nid = doc["obsidian"].copy()
    img_path_dict = {}
    img_name_dict = {}
    md_count = 0
    for filepath, file_bytes in unzipped_files.items():
        try:
            base_name, ext = filepath.rsplit(".", 1)
        except ValueError:
            continue
        if ext not in ["md", "txt", "png", "jpg", "jpeg", "gif", "svg"]:
            continue
        if len(file_bytes) > max_file_size:
            __set_running_false(uid, const.Code.TOO_LARGE_FILE, [filepath], )
            return
        if ext in ["md", "txt"]:
            if len(filepath.split("/")) > 1:
                continue
            md_count += 1
            filtered_files[filepath] = file_bytes
        else:
            img_path_dict[filepath] = file_bytes
            img_name_dict[os.path.basename(filepath)] = file_bytes

    # add new md files
    for i, (filepath, file_bytes) in enumerate(filtered_files.items()):
        base_name, ext = filepath.rsplit(".", 1)
        if base_name in existed_filename2nid:
            continue
        try:
            n, code = models.node.add(
                uid=uid,
                md=base_name,
                type_=const.NodeType.MARKDOWN.value,
            )
        except pymongo.errors.DuplicateKeyError:
            continue
        if code != const.Code.OK:
            __set_running_false(uid, code, [filepath], )
            return
        existed_filename2nid[base_name] = n["id"]
        if i % 20 == 0:
            doc, code = update_process(uid, "obsidian", int(i / md_count * 10))
            if code != const.Code.OK:
                __set_running_false(uid, code, [filepath], )
                return
            if not doc["running"]:
                break

    # update all files
    for i, (filepath, file_bytes) in enumerate(filtered_files.items()):
        base_name, ext = filepath.rsplit(".", 1)
        try:
            md = file_bytes.decode("utf-8")
        except (FileNotFoundError, OSError, UnicodeDecodeError) as e:
            logger.error(f"error: {e}. filepath: {filepath}")
            __set_running_false(uid, const.Code.FILE_OPEN_ERROR, [filepath], )
            return

        md = models.utils.replace_inner_link(
            md=md,
            exist_filename2nid=existed_filename2nid,
            img_path_dict=img_path_dict,
            img_name_dict=img_name_dict,
            min_img_size=MIN_IMAGE_SIZE,
        )
        md = base_name + "\n\n" + md
        nid = existed_filename2nid[base_name]
        n, code = models.node.update(
            uid=uid,
            nid=nid,
            md=md,
            refresh_on_same_md=True,
        )
        if code != const.Code.OK:
            __set_running_false(uid, code, [filepath])
            return
        if i % 20 == 0:
            doc, code = update_process(uid, "obsidian", int(i / md_count * 40 + 10))
            if code != const.Code.OK:
                __set_running_false(uid, code, [filepath])
                return
            if not doc["running"]:
                break

    # update for old obsidian files
    count = 0
    for base_name, nid in doc["obsidian"].items():
        if base_name not in existed_filename2nid:
            n, code = models.node.get(uid=uid, nid=nid)
            if code != const.Code.OK:
                continue
            n, code = models.node.update(
                uid=uid,
                nid=nid,
                md=n["md"],
                refresh_on_same_md=True,
            )
            if code != const.Code.OK:
                continue
        if count % 20 == 0:
            doc, code = update_process(uid, "obsidian", int(count / len(doc["obsidian"]) * 50 + 50))
            if code != const.Code.OK:
                __set_running_false(uid, code)
                return
            if not doc["running"]:
                break

        count += 1

    COLL.import_data.update_one(
        {"uid": uid},
        {"$set": {
            "obsidian": existed_filename2nid,
            "running": False,
            "problemFiles": [],
            "code": 0,
            "process": 100,
        }})


def upload_obsidian(uid: str, zipped_files: List[UploadFile]) -> const.Code:
    max_file_count = 1
    max_file_size = 1024 * 1024 * 200  # 200 mb

    doc = COLL.import_data.find_one({"uid": uid})
    if doc is None:
        doc: ImportData = {
            "_id": ObjectId(),
            "uid": uid,
            "process": 0,
            "type": "obsidian",
            "startAt": datetime.datetime.now(tz=utc),
            "running": True,
            "problemFiles": [],
            "code": 0,
            "obsidian": {},
        }
        res = COLL.import_data.insert_one(doc)
        if not res.acknowledged:
            __set_running_false(uid, const.Code.OPERATION_FAILED)
            return const.Code.OPERATION_FAILED
    elif doc["running"]:
        return const.Code.IMPORT_PROCESS_NOT_FINISHED
    _, code = update_process(
        uid=uid,
        type_="obsidian",
        process=0,
        start_at=datetime.datetime.now(tz=utc),
        running=True,
        code=0,
    )
    if code != const.Code.OK:
        __set_running_false(uid, code)
        return code

    # check file type and size and number
    if len(zipped_files) > max_file_count:
        __set_running_false(uid, const.Code.TOO_MANY_FILES)
        return const.Code.TOO_MANY_FILES

    zipped_file = zipped_files[0]
    if not zipped_file.filename.endswith(".zip"):
        __set_running_false(uid, const.Code.INVALID_FILE_TYPE)
        return const.Code.INVALID_FILE_TYPE
    if zipped_file.content_type != "application/zip":
        __set_running_false(uid, const.Code.INVALID_FILE_TYPE)
        return const.Code.INVALID_FILE_TYPE

    td = threading.Thread(
        target=upload_obsidian_thread,
        args=(uid, zipped_file, doc, max_file_size),
        daemon=True,
    )
    td.start()
    return const.Code.OK


def update_text_thread(
        uid: str,
        files: List[dict],
        max_file_size: int,
):
    for file in files:
        if not file["filename"].endswith(".md") and not file["filename"].endswith(".txt"):
            __set_running_false(uid, const.Code.INVALID_FILE_TYPE, [file["filename"]])
            return
        if file["size"] > max_file_size:
            __set_running_false(uid, const.Code.TOO_LARGE_FILE, [file["filename"]])
            return

    for i, file in enumerate(files):
        try:
            md = file["content"].decode("utf-8")
        except (FileNotFoundError, OSError) as e:
            logger.error(f"error: {e}. filepath: {file['filename']}")
            __set_running_false(uid, const.Code.FILE_OPEN_ERROR, [file["filename"]])
            return
        title = file["filename"].rsplit(".", 1)[0]
        md = title + "\n\n" + md
        try:
            n, code = models.node.add(
                uid=uid,
                md=md,
                type_=const.NodeType.MARKDOWN.value,
            )
        except pymongo.errors.DuplicateKeyError:
            continue
        if code != const.Code.OK:
            __set_running_false(uid, code, [file["filename"]])
            return
        if i % 20 == 0:
            doc, code = update_process(uid, "text", int(i / len(files) * 100))
            if code != const.Code.OK:
                __set_running_false(uid, code, [file["filename"]])
                return
            if not doc["running"]:
                break
    COLL.import_data.update_one(
        {"uid": uid},
        {"$set": {
            "running": False,
            "process": 100,
            "code": 0,
            "problemFiles": [],
        }})


def upload_text(uid: str, files: List[UploadFile]) -> const.Code:
    max_file_count = 200
    max_file_size = 1024 * 512  # 512 kb
    doc = COLL.import_data.find_one({"uid": uid})
    if doc is None:
        doc: ImportData = {
            "_id": ObjectId(),
            "uid": uid,
            "process": 0,
            "type": "text",
            "startAt": datetime.datetime.now(tz=utc),
            "running": True,
            "problemFiles": [],
            "code": 0,
            "obsidian": {},
        }
        res = COLL.import_data.insert_one(doc)
        if not res.acknowledged:
            __set_running_false(uid, const.Code.OPERATION_FAILED)
            return const.Code.OPERATION_FAILED
    elif doc["running"]:
        return const.Code.IMPORT_PROCESS_NOT_FINISHED

    _, code = update_process(
        uid,
        "text",
        0,
        start_at=datetime.datetime.now(tz=utc),
        running=True,
        code=0,
    )
    if code != const.Code.OK:
        __set_running_false(uid, code)
        return code

    if len(files) > max_file_count:
        __set_running_false(uid, const.Code.TOO_MANY_FILES)
        return const.Code.TOO_MANY_FILES

    file_list = [{
        "filename": file.filename,
        "content": file.file.read(),
        "size": file.size,
    } for file in files]

    td = threading.Thread(
        target=update_text_thread,
        args=(uid, file_list, max_file_size),
        daemon=True,
    )
    td.start()
    return const.Code.OK


def get_upload_process(uid: str) -> Optional[dict]:
    timeout_minus = 5
    doc = COLL.import_data.find_one({"uid": uid})
    if doc is None:
        return None
    now = datetime.datetime.now(tz=utc)

    # upload timeout
    if doc["running"] and \
            now.replace(tzinfo=None) - doc["startAt"].replace(tzinfo=None) \
            > datetime.timedelta(minutes=timeout_minus):
        doc["running"] = False
        COLL.import_data.update_one(
            {"uid": uid},
            {"$set": {
                "running": False,
                "code": const.Code.UPLOAD_TASK_TIMEOUT.value,
                "problemFiles": [],
            }},
        )
    return doc


def __save_image(file: UploadFile) -> Tuple[str, int]:
    # return (url, code)
    return utils.save_image(
        filename=file.filename,
        file=file.file,
        file_size=file.size,
        content_type=file.content_type,
        min_img_size=MIN_IMAGE_SIZE,
    )


def upload_image_vditor(uid: str, files: List[UploadFile]) -> dict:
    res = {
        "errFiles": [],
        "succMap": {},
    }
    u, code = models.user.get(uid=uid)
    if code != const.Code.OK:
        res["errFiles"] = [file.filename for file in files]
        return res

    for file in files:
        filename = file.filename
        if not file.content_type.startswith("image/"):
            res["errFiles"].append(filename)
            continue
        if file.size > MAX_IMAGE_SIZE:
            res["errFiles"].append(filename)
            continue
        url, code = __save_image(file)
        if code != 0:
            res["errFiles"].append(filename)
            continue
        res["succMap"][filename] = url
    return res


def fetch_image_vditor(uid: str, url: str) -> Tuple[str, const.Code]:
    u, code = models.user.get(uid=uid)
    if code != const.Code.OK:
        return "", code

    r = requests.get(url)
    if r.status_code != 200:
        return "", const.Code.FILE_OPEN_ERROR
    file = UploadFile(
        filename=url.split("/")[-1],
        file=io.BytesIO(r.content),
        headers=Headers(r.headers),
        size=len(r.content),
    )
    url, code = __save_image(file)
    if code != 0:
        return "", const.Code.FILE_OPEN_ERROR
    return url, const.Code.OK
