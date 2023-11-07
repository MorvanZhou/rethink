import datetime
import io
import os
from pathlib import Path
from typing import List, Tuple, Optional

import pymongo.errors
import requests
from PIL import Image
from bson import ObjectId
from bson.tz_util import utc
from fastapi import UploadFile
from starlette.datastructures import Headers

from rethink import const, models
from rethink.config import is_local_db, get_settings
from rethink.models import utils
from rethink.models.database import COLL
from rethink.models.tps import ImportData

MAX_FILE_SIZE = 1024 * 512  # 512 kb
MAX_FILE_COUNT = 200
MAX_IMAGE_SIZE = 1024 * 1024 * 10  # 10 mb
MIN_IMAGE_SIZE = 1024 * 128  # 128 kb


def update_process(
        uid: str,
        type_: str,
        process: int,
        start_at: datetime.datetime = None,
        running: bool = None,
) -> Tuple[Optional[ImportData], const.Code]:
    data = {"type": type_, "process": process}
    if start_at is not None:
        data["startAt"] = start_at
    if running is not None:
        data["running"] = running
    if is_local_db():
        COLL.import_data.update_one({"uid": uid}, {"$set": data})
        doc = COLL.import_data.find_one({"uid": uid})
    else:
        doc = COLL.import_data.find_one_and_update({"uid": uid}, {
            "$set": data})
    if doc is None:
        return doc, const.Code.OPERATION_FAILED
    return doc, const.Code.OK


def upload_obsidian(uid: str, files: List[UploadFile]) -> Tuple[str, const.Code]:
    doc = COLL.import_data.find_one({"uid": uid})
    if doc is None:
        doc: ImportData = {
            "_id": ObjectId(),
            "uid": uid,
            "process": 0,
            "type": "obsidian",
            "startAt": datetime.datetime.now(tz=utc),
            "running": True,
            "obsidian": {},
        }
        res = COLL.import_data.insert_one(doc)
        if not res.acknowledged:
            return "", const.Code.OPERATION_FAILED
    elif doc["running"]:
        return "", const.Code.IMPORT_PROCESS_NOT_FINISHED
    _, code = update_process(
        uid,
        "obsidian",
        0,
        start_at=datetime.datetime.now(tz=utc),
        running=True,
    )
    if code != const.Code.OK:
        return "", code

    # check file type and size and number
    if len(files) > MAX_FILE_COUNT:
        return "", const.Code.TOO_MANY_FILES
    filename2nid = doc["obsidian"].copy()
    for file in files:
        if not file.filename.endswith(".md") and not file.filename.endswith(".txt"):
            return file.filename, const.Code.INVALID_FILE_TYPE
        if file.size > MAX_FILE_SIZE:
            return file.filename, const.Code.TOO_LARGE_FILE
        filename = file.filename.rsplit(".", 1)[0]
        if filename not in filename2nid:
            filename2nid[filename] = models.utils.short_uuid()

    # add new files
    for i, file in enumerate(files):
        filename = file.filename.rsplit(".", 1)[0]
        try:
            n, code = models.node.add(
                uid=uid,
                md=filename,
                type_=const.NodeType.MARKDOWN.value,
            )
        except pymongo.errors.DuplicateKeyError:
            continue
        if code != const.Code.OK:
            return file.filename, code
        filename2nid[filename] = n["id"]
        if i % 20 == 0:
            doc, code = update_process(uid, "obsidian", int(i / len(files) * 10))
            if code != const.Code.OK:
                return file.filename, code
            if not doc["running"]:
                break

    # update new obsidian files
    for i, file in enumerate(files):
        try:
            md = file.file.read().decode("utf-8")
        except Exception:
            return file.filename, const.Code.FILE_OPEN_ERROR
        finally:
            file.file.close()
        md = models.utils.replace_inner_link(md, filename2nid)
        filename = file.filename.rsplit(".", 1)[0]
        md = filename + "\n\n" + md
        nid = filename2nid[filename]
        n, code = models.node.update(
            uid=uid,
            nid=nid,
            md=md,
            refresh_on_same_md=True,
        )
        if code != const.Code.OK:
            return file.filename, code
        if i % 20 == 0:
            doc, code = update_process(uid, "obsidian", int(i / len(files) * 40 + 10))
            if code != const.Code.OK:
                return file.filename, code
            if not doc["running"]:
                break

    # update for old obsidian files
    count = 0
    for filename, nid in doc["obsidian"].items():

        if filename not in filename2nid:
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
                return "", code
            if not doc["running"]:
                break

        count += 1
    for filename, nid in filename2nid.items():
        doc["obsidian"][filename] = nid
    doc["running"] = False
    COLL.import_data.update_one({"uid": uid}, {"$set": {"obsidian": doc["obsidian"], "running": False}})
    return "", const.Code.OK


def upload_text(uid: str, files: List[UploadFile]) -> Tuple[str, const.Code]:
    doc = COLL.import_data.find_one({"uid": uid})
    if doc is None:
        doc: ImportData = {
            "_id": ObjectId(),
            "uid": uid,
            "process": 0,
            "type": "text",
            "startAt": datetime.datetime.now(tz=utc),
            "running": True,
            "obsidian": {},
        }
        res = COLL.import_data.insert_one(doc)
        if not res.acknowledged:
            return "", const.Code.OPERATION_FAILED
    elif doc["running"]:
        return "", const.Code.IMPORT_PROCESS_NOT_FINISHED

    _, code = update_process(
        uid,
        "text",
        0,
        start_at=datetime.datetime.now(tz=utc),
        running=True,
    )
    if code != const.Code.OK:
        return "", code

    if len(files) > MAX_FILE_COUNT:
        return "", const.Code.TOO_MANY_FILES

    for file in files:
        if not file.filename.endswith(".md") and not file.filename.endswith(".txt"):
            return file.filename, const.Code.INVALID_FILE_TYPE
        if file.size > MAX_FILE_SIZE:
            return file.filename, const.Code.TOO_LARGE_FILE

    for i, file in enumerate(files):
        try:
            md = file.file.read().decode("utf-8")
        except Exception:
            return file.filename, const.Code.FILE_OPEN_ERROR
        finally:
            file.file.close()
        filename = file.filename.rsplit(".", 1)[0]
        md = filename + "\n\n" + md
        try:
            n, code = models.node.add(
                uid=uid,
                md=md,
                type_=const.NodeType.MARKDOWN.value,
            )
        except pymongo.errors.DuplicateKeyError:
            continue
        if code != const.Code.OK:
            return file.filename, code
        if i % 20 == 0:
            doc, code = update_process(uid, "text", int(i / len(files) * 100))
            if code != const.Code.OK:
                return file.filename, code
            if not doc["running"]:
                break
    COLL.import_data.update_one({"uid": uid}, {"$set": {"running": False}})
    return "", const.Code.OK


def get_upload_process(uid: str) -> Tuple[int, str, datetime.datetime, bool]:
    doc = COLL.import_data.find_one({"uid": uid})
    now = datetime.datetime.now(tz=utc)
    if doc is None:
        return 0, "", now, False
    running = doc["running"]

    # upload timeout
    if now.replace(tzinfo=None) - doc["startAt"].replace(tzinfo=None) > datetime.timedelta(minutes=5):
        running = False
        COLL.import_data.update_one(
            {"uid": uid},
            {"$set": {"running": False}}
        )
    return doc["process"], doc["type"], doc["startAt"], running


def __save_image(file: UploadFile) -> Tuple[str, int]:
    fn = Path(file.filename)
    ext = fn.suffix.lower()
    hashed = utils.file_hash(file.file)

    if file.size > MIN_IMAGE_SIZE:
        # reduce image size
        out_bytes = io.BytesIO()
        image = Image.open(file.file)
        image.save(out_bytes, format=file.content_type.split("/")[-1].upper(), quality=50, optimize=True)
        out_bytes.seek(0)
    else:
        out_bytes = file.file

    if is_local_db():
        host = os.environ["VUE_APP_API_HOST"]
        port = os.environ["VUE_APP_API_PORT"]
        if not host.startswith("http"):
            host = "http://" + host
        # upload to local storage
        img_dir = get_settings().LOCAL_STORAGE_PATH / ".data" / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        img_path = img_dir / (hashed + ext)
        if img_path.exists():
            # skip the same image
            return f"{host}:{port}/i/{img_path.name}", 0

        try:
            Image.open(out_bytes).save(img_path)
        except Exception:
            return file.filename, 1

        return f"{host}:{port}/i/{img_path.name}", 0
    else:
        # upload to cos
        try:
            url = models.files.cos.upload_from_bytes(
                out_bytes.read(),
                filename=hashed + ext,
                content_type=file.content_type,
            )
        except Exception:
            return file.filename, 1

        return url, 0


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
