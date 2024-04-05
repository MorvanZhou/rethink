import calendar
import datetime
import os
import struct
from typing import Optional, Union

from bson import ObjectId
from bson.tz_util import utc

from rethink import config, const, utils, version_manager
from rethink.depend.mongita import MongitaClientDisk
from rethink.logger import logger
from rethink.models.search_engine.engine import BaseEngine, SearchDoc, RestoreSearchDoc
from rethink.models.search_engine.engine_local import LocalSearcher
from .coll import Collections
from .indexing import remote_try_build_index
from .tps import UserFile, ImportData, UserMeta, Node

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from rethink.models.search_engine.engine_es import ESSearcher
except ImportError:
    pass


class Client:
    coll: Collections = Collections()
    mongo: Optional[Union["AsyncIOMotorClient", MongitaClientDisk]] = None
    search: Optional[BaseEngine] = None
    connection_timeout = 5

    async def init(self):
        self.init_mongo()
        await self.init_search()

        if config.is_local_db():
            await self.local_try_create_or_restore()

        else:
            # self.mongo.get_io_loop = asyncio.get_running_loop
            await remote_try_build_index(self.coll)

        await self.try_restore_search()

    def init_mongo(self):
        conf = config.get_settings()
        if config.is_local_db():
            if not conf.RETHINK_LOCAL_STORAGE_PATH.exists():
                raise FileNotFoundError(f"Path not exists: {conf.RETHINK_LOCAL_STORAGE_PATH}")
            db_path = conf.RETHINK_LOCAL_STORAGE_PATH / ".data" / "db"
            db_path.mkdir(parents=True, exist_ok=True)
            self.mongo = MongitaClientDisk(db_path)
        else:
            self.mongo = AsyncIOMotorClient(
                host=conf.DB_HOST,
                port=conf.DB_PORT,
                username=conf.DB_USER,
                password=conf.DB_PASSWORD,
                socketTimeoutMS=1000 * self.connection_timeout,
            )

        db = self.mongo[config.get_settings().DB_NAME]
        self.coll.users = db["users"]
        self.coll.nodes = db["nodes"]
        self.coll.import_data = db["importData"]
        self.coll.user_file = db["userFile"]

    async def init_search(self):
        conf = config.get_settings()
        if config.is_local_db():
            if not conf.RETHINK_LOCAL_STORAGE_PATH.exists():
                raise FileNotFoundError(f"Path not exists: {conf.RETHINK_LOCAL_STORAGE_PATH}")
            if not isinstance(self.search, LocalSearcher):
                self.search = LocalSearcher()
        else:
            if not isinstance(self.search, ESSearcher):
                self.search = ESSearcher()

        await self.search.init()

    async def drop(self):
        if self.search is not None:
            await self.search.drop()
        if self.mongo is not None:
            if isinstance(self.mongo, MongitaClientDisk):
                await self.mongo.close()
            await self.mongo.drop_database(config.get_settings().DB_NAME)

    async def local_try_add_default_user(self):
        _v = version_manager.recover.dump_dot_rethink(
            path=config.get_settings().RETHINK_LOCAL_STORAGE_PATH / ".data" / ".rethink.json"
        )

        logger.info("running at the first time, a user with initial data will be created")
        ns = const.NEW_USER_DEFAULT_NODES[_v["settings"]["language"]]
        search_docs = []

        async def create_node(md: str, to_nid: Optional[str] = None):
            title_, body_, snippet_ = utils.preprocess_md(md)
            n: Node = {
                "_id": ObjectId(),
                "id": utils.short_uuid(),
                "uid": _v["id"],
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
                "history": [],
            }
            res = await self.coll.nodes.insert_one(n)
            if not res.acknowledged:
                raise ValueError("cannot insert default node")
            search_docs.append(
                SearchDoc(
                    nid=n["id"],
                    title=title_,
                    body=body_,
                )
            )
            md_dir = config.get_settings().RETHINK_LOCAL_STORAGE_PATH / ".data" / "md"
            md_dir.mkdir(parents=True, exist_ok=True)
            with open(md_dir / f"{n['id']}.md", "w", encoding="utf-8") as f:
                f.write(md)
            return n

        n0 = await create_node(ns[0])
        _md = ns[1].format(n0["id"])
        n1 = await create_node(_md, to_nid=n0["id"])

        u: UserMeta = {
            "_id": ObjectId(_v["_id"]),
            "id": _v["id"],
            "email": _v["email"],
            "nickname": _v["nickname"],
            "avatar": _v["avatar"],
            "account": _v["email"],

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
            },
            "settings": _v["settings"],
        }
        _ = await self.coll.users.insert_one(u)

        await self.search.add_batch(
            uid=u["id"],
            docs=search_docs,
        )

    async def local_try_create_or_restore(self):  # noqa: C901
        if not config.get_settings().ONE_USER:
            return

        version_manager.migrate.to_latest_version(config.get_settings().RETHINK_LOCAL_STORAGE_PATH)
        # check if field changes
        for c, t in [
            (self.coll.users, UserMeta),
            (self.coll.nodes, Node),
            (self.coll.user_file, UserFile),
            (self.coll.import_data, ImportData),
        ]:
            doc = await c.find_one()
            if doc:
                if set(doc.keys()) != set(t.__annotations__):
                    await self.drop()
                    await self._local_restore()
                    return
        # check local files count matches db
        md_dir = config.get_settings().RETHINK_LOCAL_STORAGE_PATH / ".data" / "md"
        if md_dir.exists():
            if len(list(md_dir.glob("*.md"))) != await self.coll.nodes.count_documents({}):
                await self.drop()
                await self._local_restore()
                return
        files_dir = config.get_settings().RETHINK_LOCAL_STORAGE_PATH / ".data" / "files"
        if files_dir.exists():
            if len(list(files_dir.glob("*"))) != await self.coll.user_file.count_documents({}):
                await self.drop()
                await self._local_restore()
                return

        # try fix TypeError: can't compare offset-naive and offset-aware datetimes
        docs = self.coll.nodes.find()
        for doc in await docs.to_list(length=None):
            await self.coll.nodes.update_one(
                {"_id": doc["_id"]},
                {"$set": {"modifiedAt": doc["modifiedAt"].replace(tzinfo=utc)}},
            )
        docs = self.coll.import_data.find()
        for doc in await docs.to_list(length=None):
            await self.coll.import_data.update_one(
                {"_id": doc["_id"]},
                {"$set": {"startAt": doc["startAt"].replace(tzinfo=utc)}},
            )

        if await self.coll.users.find_one(
                {"account": const.DEFAULT_USER["email"], "source": const.UserSource.LOCAL.value}
        ) is not None:
            return

        # no default user, create one
        await self.local_try_add_default_user()

    async def _local_restore(self):
        # restore user
        _v = version_manager.recover.load_dot_rethink(
            path=config.get_settings().RETHINK_LOCAL_STORAGE_PATH / ".data" / ".rethink.json"
        )
        if _v is None:
            return

        u: UserMeta = {
            "_id": ObjectId(_v["_id"]),
            "id": _v["id"],
            "email": _v["email"],
            "nickname": _v["nickname"],
            "avatar": _v["avatar"],
            "account": _v["email"],

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
            },
            "settings": _v.get("settings", {
                "language": os.getenv("VUE_APP_LANGUAGE", const.Language.EN.value),
                "theme": const.AppTheme.LIGHT.value,
                "editorMode": const.EditorMode.WYSIWYG.value,
                "editorFontSize": 15,
                "editorCodeTheme": const.EditorCodeTheme.GITHUB.value,
                "editorSepRightWidth": 200,
                "editorSideCurrentToolId": "",
            }),
        }
        _ = await self.coll.users.insert_one(u)

        # restore nodes
        md_dir = config.get_settings().RETHINK_LOCAL_STORAGE_PATH / ".data" / "md"
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
                "_id": _oid_from_datetime(created_time),
                "id": md_path.stem,
                "uid": _v["id"],
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
                "history": [],
            }
            ns.append(n)
            search_docs.append(
                SearchDoc(
                    nid=n["id"],
                    title=title_,
                    body=body_,
                )
            )
        res = await self.coll.nodes.insert_many(ns)
        if not res.acknowledged:
            raise ValueError("cannot insert default node")
        logger.debug(f"restore nodes count: {len(res.inserted_ids)}")

        docs = []
        for f in config.get_settings().RETHINK_LOCAL_STORAGE_PATH.glob(".data/files/*"):
            filename = f.name
            fid = filename.split(".")[0]
            created_time = datetime.datetime.fromtimestamp(f.stat().st_ctime, tz=utc)
            docs.append({
                "_id": _oid_from_datetime(created_time),
                "uid": _v["id"],
                "fid": fid,
                "filename": filename,
                "size": f.stat().st_size,
            })
        res = await self.coll.user_file.insert_many(docs)
        if not res.acknowledged:
            raise ValueError("cannot insert default node")

        await self.search.drop()
        await self.search.init()
        await self.search.add_batch(
            uid=u["id"],
            docs=search_docs,
        )
        logger.debug(f"restore files count: {len(res.inserted_ids)}")

    async def try_restore_search(self):
        count_mongo = await self.coll.nodes.count_documents({})
        count_search = await self.search.count_all()
        if count_mongo == count_search:
            return
        await self.search.drop()
        await self.search.init()
        docs = await self.coll.nodes.find({}).to_list(length=None)
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
            code = await self.search.batch_restore_docs(
                uid=uid,
                docs=docs,
            )
            if code != const.Code.OK:
                raise ValueError("cannot restore search index")
        logger.debug(f"restore search index count: {count_mongo}")


def _oid_from_datetime(dt: datetime.datetime) -> ObjectId:
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


client = Client()
