import calendar
import datetime
import json
import os
import struct
from dataclasses import dataclass
from typing import Optional, Union

from bson import ObjectId
from bson.tz_util import utc
from mongita import MongitaClientDisk
from mongita.collection import Collection
from pymongo import MongoClient
from pymongo.collection import Collection as RemoteCollection

from rethink import config, const
from rethink.logger import logger
from . import utils
from .tps import UserMeta, Node, UserFile, ImportData


@dataclass
class Collections:
    users: Union[Collection, RemoteCollection] = None
    nodes: Union[Collection, RemoteCollection] = None
    import_data: Union[Collection, RemoteCollection] = None
    user_file: Union[Collection, RemoteCollection] = None


COLL = Collections()
CLIENT: Optional[Union[MongoClient, MongitaClientDisk]] = None


def set_client():
    global CLIENT
    conf = config.get_settings()
    if config.is_local_db():
        if not conf.LOCAL_STORAGE_PATH.exists():
            raise FileNotFoundError(f"Path not exists: {conf.LOCAL_STORAGE_PATH}")
        db_path = conf.LOCAL_STORAGE_PATH / ".data" / "db"
        db_path.mkdir(parents=True, exist_ok=True)
        CLIENT = MongitaClientDisk(db_path)
    else:
        CLIENT = MongoClient(
            host=conf.DB_HOST,
            port=conf.DB_PORT,
            username=conf.DB_USER,
            password=conf.DB_PASSWORD,
        )


def __remote_try_build_index():
    # try creating index
    if not isinstance(CLIENT, MongoClient):
        return

    users_info = COLL.users.index_information()
    if "id_1" not in users_info:
        COLL.users.create_index("id", unique=True)
    if "account_1_source_1" not in users_info:
        COLL.users.create_index(["account", "source"], unique=True)

    nodes_info = COLL.nodes.index_information()
    if "id_1" not in nodes_info:
        COLL.nodes.create_index("id", unique=True)
    if "uid_1_id_-1_modifiedAt_-1" not in nodes_info:
        COLL.nodes.create_index(
            [("uid", 1), ("id", -1), ("modifiedAt", -1)],
            unique=True,
        )
    if "uid_1_id_-1_inTrash_-1" not in nodes_info:
        COLL.nodes.create_index(
            [("uid", 1), ("id", -1), ("inTrash", -1)],
            unique=True,
        )
    if "uid_1_id_-1" not in nodes_info:
        # created at
        COLL.nodes.create_index(
            [("uid", 1), ("id", -1)],
            unique=True,
        )
    if "uid_1_id_-1_title_1" not in nodes_info:
        COLL.nodes.create_index(
            [("uid", 1), ("id", -1), ("title", 1)],
            unique=True,
        )

    import_data_info = COLL.import_data.index_information()
    if "uid_1" not in import_data_info:
        COLL.import_data.create_index("uid", unique=True)

    user_file_info = COLL.user_file.index_information()
    if "uid_1_fid_-1" not in user_file_info:
        COLL.user_file.create_index([("uid", 1), ("fid", -1)], unique=True)


def init():
    set_client()
    db = CLIENT[config.get_settings().DB_NAME]
    COLL.users = db["users"]
    COLL.nodes = db["nodes"]
    COLL.import_data = db["importData"]
    COLL.user_file = db["userFile"]

    if config.is_local_db():
        __local_try_create_or_restore()
    else:
        __remote_try_build_index()


def get_client():
    return CLIENT


def drop_all():
    set_client()
    for db_name in CLIENT.list_database_names():
        if db_name == "admin":
            continue
        CLIENT.drop_database(db_name)


def __local_try_add_default_user():
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
    with open(dot_rethink_path, "w") as f:
        out = u_insertion.copy()
        out["_id"] = str(out["_id"])
        json.dump(out, f, indent=2, ensure_ascii=False)

    logger.info("running at the first time, a user with initial data will be created")
    ns = const.NEW_USER_DEFAULT_NODES[u_insertion["language"]]

    def create_node(md: str):
        title_, snippet_ = utils.preprocess_md(md)
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
            "toNodeIds": [],
            "searchKeys": utils.txt2search_keys(title_),
        }
        res = COLL.nodes.insert_one(n)
        if not res.acknowledged:
            raise ValueError("cannot insert default node")
        return n

    n0 = create_node(ns[0])
    _md = ns[1].format(n0["id"])
    n1 = create_node(_md)

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
    _ = COLL.users.insert_one(u)


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


def __local_restore():
    # restore user
    dot_rethink_path = config.get_settings().LOCAL_STORAGE_PATH / ".data" / ".rethink.json"
    if not dot_rethink_path.exists():
        return
    with open(dot_rethink_path, "r") as f:
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
    _ = COLL.users.insert_one(u)

    # restore nodes
    md_dir = config.get_settings().LOCAL_STORAGE_PATH / ".data" / "md"
    if not md_dir.exists():
        return
    ns = []
    for md_path in md_dir.glob("*.md"):
        md = md_path.read_text(encoding="utf-8")
        created_time = datetime.datetime.fromtimestamp(md_path.stat().st_ctime, tz=utc)
        modified_time = datetime.datetime.fromtimestamp(md_path.stat().st_mtime, tz=utc)
        title_, snippet_ = utils.preprocess_md(md)

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
            "searchKeys": utils.txt2search_keys(title_),
        }
        ns.append(n)
    res = COLL.nodes.insert_many(ns)
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
    res = COLL.user_file.insert_many(docs)
    if not res.acknowledged:
        raise ValueError("cannot insert default node")
    logger.info(f"restore files count: {len(res.inserted_ids)}")


def __local_try_create_or_restore():
    if not config.get_settings().ONE_USER:
        return

    # check if field changes
    for c, t in [
        (COLL.users, UserMeta),
        (COLL.nodes, Node),
        (COLL.user_file, UserFile),
        (COLL.import_data, ImportData),
    ]:
        doc = c.find_one()
        if doc:
            if set(doc.keys()) != set(t.__annotations__):
                drop_all()
                __local_restore()
                return
    # check local files count matches db
    md_dir = config.get_settings().LOCAL_STORAGE_PATH / ".data" / "md"
    if md_dir.exists():
        if len(list(md_dir.glob("*.md"))) != COLL.nodes.count_documents({}):
            drop_all()
            __local_restore()
            return
    files_dir = config.get_settings().LOCAL_STORAGE_PATH / ".data" / "files"
    if files_dir.exists():
        if len(list(files_dir.glob("*"))) != COLL.user_file.count_documents({}):
            drop_all()
            __local_restore()
            return

    # try fix TypeError: can't compare offset-naive and offset-aware datetimes
    docs = COLL.nodes.find()
    for doc in docs:
        COLL.nodes.update_one(
            {"_id": doc["_id"]},
            {"$set": {"modifiedAt": doc["modifiedAt"].replace(tzinfo=utc)}},
        )
    docs = COLL.import_data.find()
    for doc in docs:
        COLL.import_data.update_one(
            {"_id": doc["_id"]},
            {"$set": {"startAt": doc["startAt"].replace(tzinfo=utc)}},
        )

    if COLL.users.find_one(
            {"account": const.DEFAULT_USER["email"], "source": const.UserSource.EMAIL.value}
    ) is not None:
        return

    # no default user, create one
    __local_try_add_default_user()
