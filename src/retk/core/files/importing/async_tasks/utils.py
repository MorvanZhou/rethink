import datetime
from typing import Optional, Tuple

from bson import ObjectId
from bson.tz_util import utc

from retk import const, config
from retk.models.client import client
from retk.models.tps import ImportData


async def check_last_task_finished(uid: str, type_: str) -> Tuple[Optional[ImportData], bool]:
    doc = await client.coll.import_data.find_one({"uid": uid})
    if doc and doc["running"]:
        await set_running_false(
            uid=uid,
            code=const.CodeEnum.IMPORT_PROCESS_NOT_FINISHED,
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
        res = await client.coll.import_data.insert_one(doc)
        if not res.acknowledged:
            await set_running_false(
                uid,
                const.CodeEnum.OPERATION_FAILED,
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
        if code != const.CodeEnum.OK:
            await set_running_false(
                uid=uid,
                code=code,
                msg="update importData process failed",
            )
            return doc, False
    return doc, True


async def finish_task(uid: str, obsidian=None):
    resp = await client.coll.import_data.update_one(
        {"uid": uid},
        {"$set": {
            "obsidian": obsidian or {},
            "running": False,
            "process": 100,
            "code": 0,
            "msg": "done",
        }})

    if resp.modified_count != 1:
        await set_running_false(
            uid=uid,
            code=const.CodeEnum.OPERATION_FAILED,
            msg="uploading importData process failed",
        )


async def update_process(
        uid: str,
        type_: str,
        process: int,
        start_at: datetime.datetime = None,
        running: bool = None,
        code: int = None,
) -> Tuple[Optional[ImportData], const.CodeEnum]:
    data = {"type": type_, "process": process}
    if start_at is not None:
        data["startAt"] = start_at
    if running is not None:
        data["running"] = running
    if code is not None:
        data["code"] = code
    if config.is_local_db():
        # local db not support find_one_and_update
        await client.coll.import_data.update_one({"uid": uid}, {"$set": data})
        doc = await client.coll.import_data.find_one({"uid": uid})
    else:
        doc = await client.coll.import_data.find_one_and_update(
            {"uid": uid},
            {"$set": data}
        )
    if doc is None:
        return doc, const.CodeEnum.OPERATION_FAILED
    return doc, const.CodeEnum.OK


async def import_set_modules():
    from retk.models.client import client
    await client.init()


async def set_running_false(
        uid: str,
        code: const.CodeEnum,
        msg: str = "",
) -> None:
    await client.coll.import_data.update_one({"uid": uid}, {"$set": {
        "running": False,
        "msg": msg,
        "code": code.value,
    }})
