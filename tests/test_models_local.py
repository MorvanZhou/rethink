import datetime
import shutil
import unittest
from io import BytesIO
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import httpx
from PIL import Image
from bson import ObjectId
from bson.tz_util import utc
from fastapi import UploadFile
from starlette.datastructures import Headers

from rethink import const, models
from rethink.models.files import queuing_upload
from rethink.models.utils import short_uuid
from . import utils


class LocalModelsTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")
        # create a fake image
        tmp_path = Path(__file__).parent / "tmp" / "fake.png"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (100, 100)).save(tmp_path)

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")
        shutil.rmtree(Path(__file__).parent / "tmp", ignore_errors=True)

    async def asyncSetUp(self) -> None:
        await models.database.drop_all()
        await models.database.init()
        u, _ = await models.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.uid = u["id"]

    async def asyncTearDown(self) -> None:
        await models.database.drop_all()
        shutil.rmtree(Path(__file__).parent / "tmp" / ".data" / "files", ignore_errors=True)
        shutil.rmtree(Path(__file__).parent / "tmp" / ".data" / "md", ignore_errors=True)

    async def test_user(self):
        _id, code = await models.user.add(
            account="aaa", source=const.UserSource.EMAIL.value,
            email="aaa", hashed="bbb", nickname="ccc", avatar="ddd", language=const.Language.EN.value)
        self.assertNotEqual("", _id)
        self.assertEqual(const.Code.OK, code)

        u, code = await models.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("rethink", u["nickname"])
        self.assertIsNotNone(u)

        u, code = await models.user.get(_id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("ccc", u["nickname"])

        u, code = await models.user.update(
            uid=_id,
            hashed="1",
            nickname="2",
            avatar="3",
            language="zh",
            node_display_method=const.NodeDisplayMethod.LIST.value,
        )
        self.assertEqual(const.Code.OK, code)

        u, code = await models.user.get(_id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("1", u["hashed"])
        self.assertEqual("2", u["nickname"])
        self.assertEqual("3", u["avatar"])
        self.assertEqual("zh", u["language"])
        self.assertEqual(const.NodeDisplayMethod.LIST.value, u["lastState"]["nodeDisplayMethod"])

        code = await models.user.disable(uid=_id)
        self.assertEqual(const.Code.OK, code)

        u, code = await models.user.get(uid=_id)
        self.assertEqual(const.Code.ACCOUNT_OR_PASSWORD_ERROR, code)
        self.assertIsNone(u)

        code = await models.user.enable(uid=_id)
        self.assertEqual(const.Code.OK, code)

        code = await models.user.disable(uid="sdwqdqw")
        self.assertEqual(const.Code.OPERATION_FAILED, code)

        code = await models.user.delete(uid=_id)
        self.assertEqual(const.Code.OK, code)

    async def test_node(self):
        node, code = await models.node.add(
            uid=self.uid, md="a" * (const.MD_MAX_LENGTH + 1), type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.NOTE_EXCEED_MAX_LENGTH, code)
        self.assertIsNone(node)

        u, code = await models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        used_space = u["usedSpace"]
        node, code = await models.node.add(
            uid=self.uid, md="[title](/qqq)\nbody", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        u, code = await models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space + len(node["md"].encode("utf-8")), u["usedSpace"])
        self.assertEqual("modifiedAt", u["lastState"]["nodeDisplaySortKey"])

        n, code = await models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title", n["title"])
        self.assertEqual("body", n["snippet"])

        ns, total = await models.database.searcher().search(uid=self.uid)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        ns, total = await models.database.searcher().search(uid=self.uid, page_size=5, page=12, sort_key="createdAt")
        self.assertEqual(0, len(ns))
        self.assertEqual(3, total)

        u, code = await models.user.update(
            uid=self.uid,
            node_display_sort_key="createdAt",
        )

        self.assertEqual(const.Code.OK, code)
        self.assertEqual("createdAt", u["lastState"]["nodeDisplaySortKey"])
        used_space = u["usedSpace"]
        n, code = await models.node.update(uid=self.uid, nid=node["id"], md="title2\nbody2")
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title2", n["title"])
        self.assertEqual("title2\nbody2", n["md"])
        self.assertEqual(const.NodeType.MARKDOWN.value, n["type"])

        u, code = await models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space + (
                len(n["md"].encode("utf-8")) -
                len(node["md"].encode("utf-8"))
        ), u["usedSpace"])

        code = await models.node.disable(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        n, code = await models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.NODE_NOT_EXIST, code)

        code = await models.node.to_trash(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)

        code = await models.node.delete(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        n, code = await models.node.get(uid=self.uid, nid=node["id"])
        self.assertIsNone(n)
        self.assertEqual(const.Code.NODE_NOT_EXIST, code)

        u, code = await models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space - len(node["md"].encode("utf-8")), u["usedSpace"])

    async def test_parse_at(self):
        nid1, _ = await models.node.add(
            uid=self.uid, md="c", type_=const.NodeType.MARKDOWN.value,
        )
        nid2, _ = await models.node.add(
            uid=self.uid, md="我133", type_=const.NodeType.MARKDOWN.value,
        )
        md = dedent(f"""title
        fffqw [@c](/n/{nid1['id']})
        fff
        [@我133](/n/{nid2['id']})
        ffq
        """)
        node, code = await models.node.add(
            uid=self.uid, md=md, type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        nodes, total = await models.database.searcher().search(
            uid=self.uid,
            query="",
            sort_key="createdAt",
            reverse=True,
            page=0,
            page_size=10,
            exclude_nids=[],
        )
        self.assertEqual(5, len(nodes))
        self.assertEqual(5, total)
        found, total = await models.database.searcher().search(uid=self.uid, query="我")
        self.assertEqual(2, len(found), msg=found)
        self.assertEqual(2, total)

        n, code = await models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(2, len(n["toNodeIds"]))

        cache = n["md"]
        n, code = await models.node.update(uid=self.uid, nid=node["id"], md=f'{cache}xxxx')
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(cache + "xxxx", n["md"])

        n, code = await models.node.get(uid=self.uid, nid=nid1['id'])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(1, len(n["fromNodeIds"]))

        n, code = await models.node.update(uid=self.uid, nid=node["id"], md=n["title"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(0, len(n["toNodeIds"]))

        n, code = await models.node.get(uid=self.uid, nid=nid1['id'])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(0, len(n["fromNodeIds"]))

    async def test_add_set(self):
        node, code = await models.node.add(
            uid=self.uid, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(0, len(node["toNodeIds"]))
        self.assertEqual(const.Code.OK, code)

        res = await models.db_ops.node_add_to_set(node["id"], "toNodeIds", short_uuid())
        self.assertEqual(1, res.modified_count)
        node, code = await models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(1, len(node["toNodeIds"]))

    async def test_cursor_text(self):
        n1, code = await models.node.add(
            uid=self.uid, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        n2, code = await models.node.add(
            uid=self.uid, md="title2\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)

        recom, total = await models.search.cursor_query(
            uid=self.uid,
            nid=n2["id"],
            query="text",
            page=0,
            page_size=10,
        )
        self.assertEqual(1, len(recom))
        self.assertEqual(1, total)

        recom, total = await models.search.cursor_query(
            uid=self.uid,
            nid=n2["id"],  # exclude the second node
            query="",  # return recent nodes only
            page=0,
            page_size=10,
        )
        self.assertEqual(2, len(recom))
        self.assertEqual(2, total)

        code = await models.search.add_recent_cursor_search(self.uid, n1["id"], n2["id"])
        self.assertEqual(const.Code.OK, code)

        recom, total = await models.search.cursor_query(
            uid=self.uid,
            nid=n1["id"],  # exclude the second node
            query="",
            page=0,
            page_size=10,
        )
        self.assertEqual(3, len(recom))
        self.assertEqual(3, total)
        self.assertEqual("Welcome to Rethink", recom[2].title)

    async def test_to_trash(self):
        n1, code = await models.node.add(
            uid=self.uid, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        n2, code = await models.node.add(
            uid=self.uid, md="title2\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)

        code = await models.node.to_trash(self.uid, n1["id"])
        self.assertEqual(const.Code.OK, code)

        ns, total = await models.node.get_nodes_in_trash(self.uid, 0, 10)
        self.assertEqual(1, len(ns))
        self.assertEqual(1, total)
        self.assertEqual(n1["id"], ns[0]["id"])

        ns, total = await models.database.searcher().search(self.uid, query="")
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        code = await models.node.restore_from_trash(self.uid, n1["id"])
        self.assertEqual(const.Code.OK, code)
        nodes, total = await models.database.searcher().search(self.uid, query="")
        self.assertEqual(4, len(nodes))
        self.assertEqual(4, total)

    async def test_search(self):
        code = await models.search.put_recent_search(self.uid, "a")
        self.assertEqual(const.Code.OK, code)
        await models.search.put_recent_search(self.uid, "c")
        await models.search.put_recent_search(self.uid, "b")

        queries = await models.search.get_recent_search(self.uid)
        self.assertEqual(["b", "c", "a"], queries)

    async def test_batch(self):
        ns = []
        for i in range(10):
            n, code = await models.node.add(
                uid=self.uid, md=f"title{i}\ntext", type_=const.NodeType.MARKDOWN.value
            )
            self.assertEqual(const.Code.OK, code)
            ns.append(n)

        base_count = 2

        code = await models.node.batch_to_trash(self.uid, [n["id"] for n in ns[:4]])
        self.assertEqual(const.Code.OK, code)
        nodes, total = await models.database.searcher().search(self.uid, query="")
        self.assertEqual(6 + base_count, len(nodes))
        self.assertEqual(6 + base_count, total)

        tns, total = await models.node.get_nodes_in_trash(self.uid, 0, 10)
        self.assertEqual(4, total)
        self.assertEqual(4, len(tns))

        code = await models.node.restore_batch_from_trash(self.uid, [n["id"] for n in tns[:2]])
        self.assertEqual(const.Code.OK, code)
        nodes, total = await models.database.searcher().search(self.uid)
        self.assertEqual(8 + base_count, len(nodes))
        self.assertEqual(8 + base_count, total)

        code = await models.node.batch_delete(self.uid, [n["id"] for n in tns[2:4]])
        self.assertEqual(const.Code.OK, code)
        tns, total = await models.node.get_nodes_in_trash(self.uid, 0, 10)
        self.assertEqual(0, total)
        self.assertEqual(0, len(tns))

    async def test_files_upload_process(self):
        now = datetime.datetime.now(tz=utc)
        doc: models.tps.ImportData = {
            "_id": ObjectId(),
            "uid": "xxx",
            "process": 0,
            "type": "text",
            "startAt": now,
            "running": True,
            "obsidian": {},
            "msg": "",
            "code": const.Code.OK.value,
        }
        res = await models.database.COLL.import_data.insert_one(doc)
        self.assertTrue(res.acknowledged)

        doc, code = await queuing_upload.update_process("xxx", "obsidian", 10)
        self.assertEqual(const.Code.OK, code)

        doc = await models.files.get_upload_process("xxx")
        self.assertEqual(10, doc["process"])
        self.assertEqual("obsidian", doc["type"])
        self.assertEqual(now, doc["startAt"])
        self.assertTrue(doc["running"])

        await models.database.COLL.import_data.delete_one({"uid": "xxx"})

    async def test_update_title_and_from_nodes_updates(self):
        n1, code = await models.node.add(
            uid=self.uid, md="title1\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        n2, code = await models.node.add(
            uid=self.uid, md=f"title2\n[@title1](/n/{n1['id']})", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)

        n1, code = await models.node.update(uid=self.uid, nid=n1["id"], md="title1Changed\ntext")
        self.assertEqual(const.Code.OK, code)
        n2, code = await models.node.get(uid=self.uid, nid=n2["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(f"title2\n[@title1Changed](/n/{n1['id']})", n2["md"])

    async def test_upload_image_vditor(self):
        u, code = await models.user.get(self.uid)
        used_space = u["usedSpace"]
        p = Path(__file__).parent / "tmp" / "fake.png"

        image = Image.open(p)
        buf = BytesIO()
        image.save(buf, format="png")
        size = buf.tell()
        img_file = UploadFile(
            buf, filename="fake.png", size=size,
            headers=Headers({"content-type": "image/png"})
        )
        res = await models.files.upload_image_vditor(self.uid, [img_file])
        self.assertIn("fake.png", res["succMap"])
        self.assertTrue(".png" in res["succMap"]["fake.png"])
        local_file = Path(__file__).parent / "tmp" / ".data" / res["succMap"]["fake.png"][1:]
        self.assertTrue(local_file.exists())
        local_file.unlink()
        image.close()
        buf.close()
        await img_file.close()

        u, code = await models.user.get(self.uid)
        self.assertEqual(used_space + size, u["usedSpace"])

    @patch(
        "rethink.models.files.upload.httpx.AsyncClient.get",
    )
    async def test_fetch_image_vditor(self, mock_get):
        f = open(Path(__file__).parent / "tmp" / "fake.png", "rb")
        mock_get.return_value = httpx.Response(
            200,
            content=f.read(),
            headers={"content-type": "image/png"}
        )

        u, code = await models.user.get(self.uid)
        used_space = u["usedSpace"]

        url = "https://rethink.run/favicon.png"
        new_url, code = await models.files.fetch_image_vditor(self.uid, url)
        self.assertEqual(const.Code.OK, code)
        self.assertTrue(new_url.endswith(".png"))
        self.assertTrue(new_url.startswith("/"))
        local_file = Path(__file__).parent / "tmp" / ".data" / new_url[1:]
        self.assertTrue(local_file.exists())
        local_file.unlink()

        u, code = await models.user.get(self.uid)
        self.assertEqual(used_space + f.tell(), u["usedSpace"])
        f.close()

    async def test_update_used_space(self):
        u, code = await models.user.get(self.uid)
        base_used_space = u["usedSpace"]
        for delta, value in [
            (100, 100),
            (100, 200),
            (0, 200),
            (-3000, 0),
            (20.1, 20.1),
        ]:
            code = await models.user.update_used_space(self.uid, delta)
            self.assertEqual(const.Code.OK, code)
            u, code = await models.user.get(self.uid)
            self.assertEqual(const.Code.OK, code)
            now = u["usedSpace"] - base_used_space
            if now < 0:
                now = 0
                base_used_space = 0
            self.assertAlmostEqual(value, now, msg=f"delta: {delta}, value: {value}")
