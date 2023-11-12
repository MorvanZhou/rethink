import datetime
import os
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
from .tps import UserMeta, UserNodeIds, Node


@dataclass
class Collections:
    users: Union[Collection, RemoteCollection] = None
    unids: Union[Collection, RemoteCollection] = None
    nodes: Union[Collection, RemoteCollection] = None
    import_data: Union[Collection, RemoteCollection] = None
    user_file: Union[Collection, RemoteCollection] = None


COLL = Collections()
CLIENT: Optional[Union[MongoClient, MongitaClientDisk]] = None


def set_client():
    global CLIENT
    conf = config.get_settings()
    if config.is_local_db():
        if not os.path.exists(conf.LOCAL_STORAGE_PATH):
            raise FileNotFoundError(f"Path not exists: {conf.LOCAL_STORAGE_PATH}")
        dot_data_path = os.path.join(conf.LOCAL_STORAGE_PATH, ".data")
        os.makedirs(dot_data_path, exist_ok=True)
        CLIENT = MongitaClientDisk(dot_data_path)
    else:
        CLIENT = MongoClient(
            host=conf.DB_HOST,
            port=conf.DB_PORT,
            username=conf.DB_USER,
            password=conf.DB_PASSWORD,
        )


def init():
    set_client()
    db = CLIENT[config.get_settings().DB_NAME]
    COLL.users = db["users"]
    COLL.unids = db["unids"]
    COLL.nodes = db["nodes"]
    COLL.import_data = db["importData"]
    COLL.user_file = db["userFile"]

    if config.is_local_db():
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

    if isinstance(CLIENT, MongoClient):
        # try creating index
        COLL.users.create_index("id", unique=True)
        COLL.users.create_index(["account", "source"], unique=True)
        COLL.nodes.create_index("id", unique=True)
        COLL.unids.create_index("id", unique=True)
        COLL.import_data.create_index("uid", unique=True)
        COLL.user_file.create_index(["uid", "fid"], unique=True)

    # try add default user
    if config.get_settings().ONE_USER:
        if COLL.users.find_one(
                {"account": const.DEFAULT_USER["email"], "source": const.UserSource.EMAIL.value}
        ) is not None:
            return

        logger.info("running at the first time, a user with initial data will be created")
        language = os.getenv("VUE_APP_LANGUAGE", const.Language.EN.value)
        ns = const.NEW_USER_DEFAULT_NODES[language]

        def create_node(md: str):
            title_, snippet_ = utils.preprocess_md(md)
            n: Node = {
                "_id": ObjectId(),
                "id": utils.short_uuid(),
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
            "_id": ObjectId(),
            "id": utils.short_uuid(),
            "source": const.UserSource.LOCAL.value,
            "account": const.DEFAULT_USER["email"],
            "email": const.DEFAULT_USER["email"],
            "hashed": "",
            "avatar": const.DEFAULT_USER["avatar"],
            "disabled": False,
            "nickname": const.DEFAULT_USER["nickname"],
            "modifiedAt": datetime.datetime.now(tz=utc),
            "language": language,
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
        unids: UserNodeIds = {
            "_id": u["_id"],
            "id": u["id"],
            "nodeIds": [n0["id"], n1["id"]],
        }
        _ = COLL.unids.insert_one(unids)


def get_client():
    return CLIENT


def drop_all():
    set_client()
    for db_name in CLIENT.list_database_names():
        if db_name == "admin":
            continue
        CLIENT.drop_database(db_name)
