import calendar
import datetime
import json
import os
import struct
from dataclasses import dataclass
from typing import Optional, Union, TYPE_CHECKING

from bson import ObjectId
from bson.tz_util import utc

from rethink import config, const
from rethink.logger import logger
from rethink.mongita import MongitaClientDisk
from rethink.mongita.collection import Collection
from . import utils
from .search_engine.engine import BaseEngine, SearchDoc, RestoreSearchDoc
from .search_engine.engine_local import LocalSearcher
from .tps import UserMeta, Node, UserFile, ImportData

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
    from .search_engine.engine_es import ESSearcher


@dataclass
class Collections:
    users: Union[Collection, "AsyncIOMotorCollection"] = None
    nodes: Union[Collection, "AsyncIOMotorCollection"] = None
    import_data: Union[Collection, "AsyncIOMotorCollection"] = None
    user_file: Union[Collection, "AsyncIOMotorCollection"] = None


COLL = Collections()
CLIENT: Optional[Union["AsyncIOMotorClient", MongitaClientDisk]] = None
SEARCHER: Optional[BaseEngine] = None


def searcher() -> BaseEngine:
    if SEARCHER is None:
        raise ValueError("searcher not initialized")
    return SEARCHER


async def set_client():
    global CLIENT, SEARCHER
    conf = config.get_settings()
    if config.is_local_db():
        if not conf.LOCAL_STORAGE_PATH.exists():
            raise FileNotFoundError(f"Path not exists: {conf.LOCAL_STORAGE_PATH}")
        db_path = conf.LOCAL_STORAGE_PATH / ".data" / "db"
        db_path.mkdir(parents=True, exist_ok=True)
        if not isinstance(SEARCHER, LocalSearcher):
            SEARCHER = LocalSearcher()
        CLIENT = MongitaClientDisk(db_path)
    else:
        from .search_engine.engine_es import ESSearcher
        if not isinstance(SEARCHER, ESSearcher):
            SEARCHER = ESSearcher()
        from motor.motor_asyncio import AsyncIOMotorClient
        CLIENT = AsyncIOMotorClient(
            host=conf.DB_HOST,
            port=conf.DB_PORT,
            username=conf.DB_USER,
            password=conf.DB_PASSWORD,
            socketTimeoutMS=1000 * 5,
        )


def set_coll():
    db = CLIENT[config.get_settings().DB_NAME]
    COLL.users = db["users"]
    COLL.nodes = db["nodes"]
    COLL.import_data = db["importData"]
    COLL.user_file = db["userFile"]


async def init():
    await set_client()
    await SEARCHER.init()
    set_coll()

    if config.is_local_db():
        await __local_try_create_or_restore()

    else:
        # CLIENT.get_io_loop = asyncio.get_running_loop
        await __remote_try_build_index()

    await __try_restore_search()


async def drop_all():
    await set_client()
    await CLIENT.drop_database(config.get_settings().DB_NAME)
    global SEARCHER
    if SEARCHER:
        await SEARCHER.drop()


async def __remote_try_build_index():
    # try creating index
    from motor.motor_asyncio import AsyncIOMotorClient
    if not isinstance(CLIENT, AsyncIOMotorClient):
        return

    users_info = await COLL.users.index_information()
    if "id_1" not in users_info:
        await COLL.users.create_index("id", unique=True)
    if "account_1_source_1" not in users_info:
        await COLL.users.create_index(["account", "source"], unique=True)

    nodes_info = await COLL.nodes.index_information()
    if "id_1" not in nodes_info:
        await COLL.nodes.create_index("id", unique=True)
    if "uid_1_id_-1" not in nodes_info:
        # created at
        await COLL.nodes.create_index(
            [("uid", 1), ("id", -1)],
            unique=True,
        )

    import_data_info = await COLL.import_data.index_information()
    if "uid_1" not in import_data_info:
        await COLL.import_data.create_index("uid", unique=True)

    user_file_info = await COLL.user_file.index_information()
    if "uid_1_fid_-1" not in user_file_info:
        await COLL.user_file.create_index([("uid", 1), ("fid", -1)], unique=True)


async def __local_try_add_default_user():
    dot_rethink_path = config.get_settings().LOCAL_STORAGE_PATH / ".data" / ".rethink.json"
    u_insertion = {
        "_id": ObjectId(),
        "id": utils.short_uuid(),
        "email": const.DEFAULT_USER["email"],
        "nickname": const.DEFAULT_USER["nickname"],
        "avatar": const.DEFAULT_USER["avatar"],
        "account": const.DEFAULT_USER["email"],
        "language": os.getenv("VUE_APP_LANGUAGE", const.Language.EN.value),
    }
    with open(dot_rethink_path, "w", encoding="utf-8") as f:
        out = u_insertion.copy()
        out["_id"] = str(out["_id"])
        json.dump(out, f, indent=2, ensure_ascii=False)

    logger.info("running at the first time, a user with initial data will be created")
    ns = const.NEW_USER_DEFAULT_NODES[u_insertion["language"]]
    search_docs = []

    async def create_node(md: str, to_nid: Optional[str] = None):
        title_, body_, snippet_ = utils.preprocess_md(md)
        n: Node = {
            "_id": ObjectId(),
            "id": utils.short_uuid(),
            "uid": u_insertion["id"],
            "title": title_,
            "snippet": snippet_,
            "md": md,
            "type": const.NodeType.MARKDOWN.value,
            "disabled": False,
            "inTrash": False,
            "modifiedAt": datetime.datetime.now(tz=utc),
            "inTrashAt": None,
            "fromNodeIds": [],
            "toNodeIds": [] if to_nid is None else [to_nid],
        }
        res = await COLL.nodes.insert_one(n)
        if not res.acknowledged:
            raise ValueError("cannot insert default node")
        search_docs.append(
            SearchDoc(
                nid=n["id"],
                title=title_,
                body=body_,
            )
        )
        md_dir = config.get_settings().LOCAL_STORAGE_PATH / ".data" / "md"
        md_dir.mkdir(parents=True, exist_ok=True)
        with open(md_dir / f"{n['id']}.md", "w", encoding="utf-8") as f:
            f.write(md)
        return n

    n0 = await create_node(ns[0])
    _md = ns[1].format(n0["id"])
    n1 = await create_node(_md, to_nid=n0["id"])

    u: UserMeta = {
        "_id": ObjectId(u_insertion["_id"]),
        "id": u_insertion["id"],
        "email": u_insertion["email"],
        "nickname": u_insertion["nickname"],
        "avatar": u_insertion["avatar"],
        "account": u_insertion["email"],
        "language": u_insertion["language"],

        "source": const.UserSource.LOCAL.value,
        "hashed": "",
        "disabled": False,
        "modifiedAt": datetime.datetime.now(tz=utc),
        "usedSpace": 0,
        "type": const.USER_TYPE.NORMAL.id,
        "lastState": {
            "recentCursorSearchSelectedNIds": [n0["id"], n1["id"]],
            "recentSearch": [],
            "nodeDisplayMethod": const.NodeDisplayMethod.CARD.value,
            "nodeDisplaySortKey": "modifiedAt"
        }
    }
    _ = await COLL.users.insert_one(u)

    await SEARCHER.add_batch(
        uid=u["id"],
        docs=search_docs,
    )


def __oid_from_datetime(dt: datetime.datetime) -> ObjectId:
    offset = dt.utcoffset()
    if offset is not None:
        dt = dt - offset
    timestamp = calendar.timegm(dt.timetuple())
    oid = struct.pack(">I", timestamp)
    oid += ObjectId._random()
    with ObjectId._inc_lock:
        oid += struct.pack(">I", ObjectId._inc)[1:4]
        ObjectId._inc = (ObjectId._inc + 1) % (0xFFFFFF + 1)
    return ObjectId(oid)


async def __local_restore():
    # restore user
    dot_rethink_path = config.get_settings().LOCAL_STORAGE_PATH / ".data" / ".rethink.json"
    if not dot_rethink_path.exists():
        return
    with open(dot_rethink_path, "r", encoding="utf-8") as f:
        u_insertion = json.load(f)

    u: UserMeta = {
        "_id": ObjectId(u_insertion["_id"]),
        "id": u_insertion["id"],
        "email": u_insertion["email"],
        "nickname": u_insertion["nickname"],
        "avatar": u_insertion["avatar"],
        "account": u_insertion["email"],
        "language": u_insertion["language"],

        "source": const.UserSource.LOCAL.value,
        "hashed": "",
        "disabled": False,
        "modifiedAt": datetime.datetime.now(tz=utc),
        "usedSpace": 0,
        "type": const.USER_TYPE.NORMAL.id,
        "lastState": {
            "recentCursorSearchSelectedNIds": [],
            "recentSearch": [],
            "nodeDisplayMethod": const.NodeDisplayMethod.CARD.value,
            "nodeDisplaySortKey": "modifiedAt"
        }
    }
    _ = await COLL.users.insert_one(u)

    # restore nodes
    md_dir = config.get_settings().LOCAL_STORAGE_PATH / ".data" / "md"
    if not md_dir.exists():
        return
    ns = []
    search_docs = []
    for md_path in md_dir.glob("*.md"):
        md = md_path.read_text(encoding="utf-8")
        created_time = datetime.datetime.fromtimestamp(md_path.stat().st_ctime, tz=utc)
        modified_time = datetime.datetime.fromtimestamp(md_path.stat().st_mtime, tz=utc)
        title_, body_, snippet_ = utils.preprocess_md(md)

        n: Node = {
            "_id": __oid_from_datetime(created_time),
            "id": md_path.stem,
            "uid": u_insertion["id"],
            "title": title_,
            "snippet": snippet_,
            "md": md,
            "type": const.NodeType.MARKDOWN.value,
            "disabled": False,
            "inTrash": False,
            "modifiedAt": modified_time,
            "inTrashAt": None,
            "fromNodeIds": [],
            "toNodeIds": [],
        }
        ns.append(n)
        search_docs.append(
            SearchDoc(
                nid=n["id"],
                title=title_,
                body=body_,
            )
        )
    res = await COLL.nodes.insert_many(ns)
    if not res.acknowledged:
        raise ValueError("cannot insert default node")
    logger.info(f"restore nodes count: {len(res.inserted_ids)}")

    docs = []
    for f in config.get_settings().LOCAL_STORAGE_PATH.glob(".data/files/*"):
        filename = f.name
        fid = filename.split(".")[0]
        created_time = datetime.datetime.fromtimestamp(f.stat().st_ctime, tz=utc)
        docs.append({
            "_id": __oid_from_datetime(created_time),
            "uid": u_insertion["id"],
            "fid": fid,
            "filename": filename,
            "size": f.stat().st_size,
        })
    res = await COLL.user_file.insert_many(docs)
    if not res.acknowledged:
        raise ValueError("cannot insert default node")

    await SEARCHER.drop()
    await SEARCHER.init()
    await SEARCHER.add_batch(
        uid=u["id"],
        docs=search_docs,
    )
    logger.info(f"restore files count: {len(res.inserted_ids)}")


async def __local_try_create_or_restore():
    if not config.get_settings().ONE_USER:
        return

    # check if field changes
    for c, t in [
        (COLL.users, UserMeta),
        (COLL.nodes, Node),
        (COLL.user_file, UserFile),
        (COLL.import_data, ImportData),
    ]:
        doc = await c.find_one()
        if doc:
            if set(doc.keys()) != set(t.__annotations__):
                await drop_all()
                await __local_restore()
                return
    # check local files count matches db
    md_dir = config.get_settings().LOCAL_STORAGE_PATH / ".data" / "md"
    if md_dir.exists():
        if len(list(md_dir.glob("*.md"))) != await COLL.nodes.count_documents({}):
            await drop_all()
            await __local_restore()
            return
    files_dir = config.get_settings().LOCAL_STORAGE_PATH / ".data" / "files"
    if files_dir.exists():
        if len(list(files_dir.glob("*"))) != await COLL.user_file.count_documents({}):
            await drop_all()
            await __local_restore()
            return

    # try fix TypeError: can't compare offset-naive and offset-aware datetimes
    docs = COLL.nodes.find()
    for doc in await docs.to_list(length=None):
        await COLL.nodes.update_one(
            {"_id": doc["_id"]},
            {"$set": {"modifiedAt": doc["modifiedAt"].replace(tzinfo=utc)}},
        )
    docs = COLL.import_data.find()
    for doc in await docs.to_list(length=None):
        await COLL.import_data.update_one(
            {"_id": doc["_id"]},
            {"$set": {"startAt": doc["startAt"].replace(tzinfo=utc)}},
        )

    if await COLL.users.find_one(
            {"account": const.DEFAULT_USER["email"], "source": const.UserSource.LOCAL.value}
    ) is not None:
        return

    # no default user, create one
    await __local_try_add_default_user()


async def __try_restore_search():
    count_mongo = await COLL.nodes.count_documents({})
    count_search = await SEARCHER.count_all()
    if count_mongo == count_search:
        return
    await SEARCHER.drop()
    await SEARCHER.init()
    docs = await COLL.nodes.find({}).to_list(length=None)
    search_docs = {}
    for doc in docs:
        if doc["uid"] not in search_docs:
            search_docs[doc["uid"]] = []

        search_docs[doc["uid"]].append(
            RestoreSearchDoc(
                nid=doc["id"],
                title=doc["title"],
                body=doc["md"],
                createdAt=doc["_id"].generation_time,
                modifiedAt=doc["modifiedAt"],
                disabled=doc["disabled"],
                inTrash=doc["inTrash"],
            )
        )
    for uid, docs in search_docs.items():
        code = await SEARCHER.batch_restore_docs(
            uid=uid,
            docs=docs,
        )
        if code != const.Code.OK:
            raise ValueError("cannot restore search index")
    logger.info(f"restore search index count: {count_mongo}")
