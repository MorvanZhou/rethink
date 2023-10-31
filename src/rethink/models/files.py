from typing import List, Tuple

import pymongo.errors
from bson import ObjectId
from fastapi import UploadFile

from rethink import const, models
from rethink.models.database import COLL
from rethink.models.tps import ImportData

MAX_FILE_SIZE = 1024 * 512  # 512 kb
MAX_FILE_COUNT = 200


def upload_obsidian(uid: str, files: List[UploadFile]) -> Tuple[str, const.Code]:
    first_import = False
    doc = COLL.import_data.find_one({"uid": uid})
    if doc is None:
        first_import = True
        doc: ImportData = {"_id": ObjectId(), "uid": uid, "obsidian": {}}

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
    for file in files:
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

    # update new obsidian files
    for file in files:
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

    # update for old obsidian files
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

    for filename, nid in filename2nid.items():
        doc["obsidian"][filename] = nid
    if first_import:
        COLL.import_data.insert_one(doc)
    else:
        COLL.import_data.update_one({"uid": uid}, {"$set": {"obsidian": doc["obsidian"]}})
    return "", const.Code.OK


def upload_text(uid: str, files: List[UploadFile]) -> Tuple[str, const.Code]:
    if len(files) > MAX_FILE_COUNT:
        return "", const.Code.TOO_MANY_FILES

    for file in files:
        if not file.filename.endswith(".md") and not file.filename.endswith(".txt"):
            return file.filename, const.Code.INVALID_FILE_TYPE
        if file.size > MAX_FILE_SIZE:
            return file.filename, const.Code.TOO_LARGE_FILE

    for file in files:
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
    return "", const.Code.OK
