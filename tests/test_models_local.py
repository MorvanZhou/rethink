import datetime
import os
import unittest
from io import BytesIO
from pathlib import Path
from textwrap import dedent

import requests
from PIL import Image
from bson import ObjectId
from bson.tz_util import utc
from fastapi import UploadFile
from starlette.datastructures import Headers

from rethink import const, models
from rethink.models.utils import short_uuid
from . import utils


class LocalModelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")
        models.database.drop_all()

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    def setUp(self) -> None:
        models.database.init()
        u, _ = models.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.uid = u["id"]

    def tearDown(self) -> None:
        models.database.drop_all()

    def test_user(self):
        _id, code = models.user.add(
            account="aaa", source=const.UserSource.EMAIL.value,
            email="aaa", hashed="bbb", nickname="ccc", avatar="ddd", language=const.Language.EN.value)
        self.assertNotEqual("", _id)
        self.assertEqual(const.Code.OK, code)

        u, code = models.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("rethink", u["nickname"])
        self.assertIsNotNone(u)

        u, code = models.user.get(_id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("ccc", u["nickname"])

        u, code = models.user.update(
            uid=_id,
            email="a@a.com",
            hashed="1",
            nickname="2",
            avatar="3",
            language="zh",
            node_display_method=const.NodeDisplayMethod.LIST.value,
        )
        self.assertEqual(const.Code.OK, code)

        u, code = models.user.get(_id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("a@a.com", u["email"])
        self.assertEqual("1", u["hashed"])
        self.assertEqual("2", u["nickname"])
        self.assertEqual("3", u["avatar"])
        self.assertEqual("zh", u["language"])
        self.assertEqual(const.NodeDisplayMethod.LIST.value, u["lastState"]["nodeDisplayMethod"])

        code = models.user.disable(uid=_id)
        self.assertEqual(const.Code.OK, code)

        u, code = models.user.get(uid=_id)
        self.assertEqual(const.Code.ACCOUNT_OR_PASSWORD_ERROR, code)
        self.assertIsNone(u)

        code = models.user.enable(uid=_id)
        self.assertEqual(const.Code.OK, code)

        code = models.user.disable(uid="sdwqdqw")
        self.assertEqual(const.Code.OPERATION_FAILED, code)

        code = models.user.delete(uid=_id)
        self.assertEqual(const.Code.OK, code)

    def test_node(self):
        node, code = models.node.add(
            uid=self.uid, md="a" * (const.MD_MAX_LENGTH + 1), type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.NOTE_EXCEED_MAX_LENGTH, code)
        self.assertIsNone(node)

        u, code = models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        used_space = u["usedSpace"]
        node, code = models.node.add(
            uid=self.uid, md="[title](/qqq)\nbody", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        u, code = models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space + len(node["md"].encode("utf-8")), u["usedSpace"])
        self.assertEqual("modifiedAt", u["lastState"]["nodeDisplaySortKey"])

        n, code = models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title", n["title"])
        self.assertEqual("body", n["snippet"])

        ns, total = models.search.user_node(uid=self.uid)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        ns, total = models.search.user_node(uid=self.uid, page_size=5, page=12, sort_key="createdAt")
        self.assertEqual(0, len(ns))
        self.assertEqual(3, total)

        u, code = models.user.update(
            uid=self.uid,
            node_display_sort_key="createdAt",
        )

        self.assertEqual(const.Code.OK, code)
        self.assertEqual("createdAt", u["lastState"]["nodeDisplaySortKey"])
        used_space = u["usedSpace"]
        n, code = models.node.update(uid=self.uid, nid=node["id"], md="title2\nbody2")
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title2", n["title"])
        self.assertEqual("title2\nbody2", n["md"])
        self.assertEqual(const.NodeType.MARKDOWN.value, n["type"])

        u, code = models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space + (
                len(n["md"].encode("utf-8")) -
                len(node["md"].encode("utf-8"))
        ), u["usedSpace"])

        code = models.node.disable(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        n, code = models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.NODE_NOT_EXIST, code)

        code = models.node.to_trash(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)

        code = models.node.delete(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        n, code = models.node.get(uid=self.uid, nid=node["id"])
        self.assertIsNone(n)
        self.assertEqual(const.Code.NODE_NOT_EXIST, code)

        u, code = models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space - len(node["md"].encode("utf-8")), u["usedSpace"])

    def test_parse_at(self):
        nid1, _ = models.node.add(
            uid=self.uid, md="c", type_=const.NodeType.MARKDOWN.value,
        )
        nid2, _ = models.node.add(
            uid=self.uid, md="我133", type_=const.NodeType.MARKDOWN.value,
        )
        md = dedent(f"""title
        fffqw [@c](/n/{nid1['id']})
        fff 
        [@我133](/n/{nid2['id']})
        ffq
        """)
        node, code = models.node.add(
            uid=self.uid, md=md, type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        nodes, total = models.search.user_node(uid=self.uid)
        self.assertEqual(5, len(nodes))
        self.assertEqual(5, total)
        found, total = models.search.user_node(uid=self.uid, query="我")
        self.assertEqual(2, len(found), msg=found)
        self.assertEqual(5, total)

        n, code = models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(2, len(n["toNodeIds"]))

        cache = n["md"]
        n, code = models.node.update(uid=self.uid, nid=node["id"], md=f'{cache}xxxx')
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(cache + "xxxx", n["md"])

        n, code = models.node.get(uid=self.uid, nid=nid1['id'])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(1, len(n["fromNodeIds"]))

        n, code = models.node.update(uid=self.uid, nid=node["id"], md=n["title"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(0, len(n["toNodeIds"]))

        n, code = models.node.get(uid=self.uid, nid=nid1['id'])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(0, len(n["fromNodeIds"]))

    def test_add_set(self):
        node, code = models.node.add(
            uid=self.uid, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(0, len(node["toNodeIds"]))
        self.assertEqual(const.Code.OK, code)

        res = models.db_ops.node_add_to_set(node["id"], "toNodeIds", short_uuid())
        self.assertEqual(1, res.modified_count)
        node, code = models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(1, len(node["toNodeIds"]))

    def test_cursor_text(self):
        n1, code = models.node.add(
            uid=self.uid, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        n2, code = models.node.add(
            uid=self.uid, md="title2\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)

        recom = models.node.cursor_query(
            uid=self.uid,
            nid=n2["id"],
            cursor_text="te",
        )
        self.assertEqual(2, len(recom))

        recom = models.node.cursor_query(
            uid=self.uid,
            nid=n2["id"],  # exclude the second node
            cursor_text="",
        )
        self.assertEqual(2, len(recom))

        code = models.search.add_recent_cursor_search(self.uid, n1["id"], n2["id"])
        self.assertEqual(const.Code.OK, code)

        recom = models.node.cursor_query(
            uid=self.uid,
            nid=n1["id"],  # exclude the second node
            cursor_text="",
        )
        self.assertEqual(3, len(recom))
        self.assertEqual("Welcome to Rethink", recom[2]["title"])

    def test_to_trash(self):
        n1, code = models.node.add(
            uid=self.uid, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        n2, code = models.node.add(
            uid=self.uid, md="title2\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)

        code = models.node.to_trash(self.uid, n1["id"])
        self.assertEqual(const.Code.OK, code)

        ns, total = models.node.get_nodes_in_trash(self.uid, 0, 10)
        self.assertEqual(1, len(ns))
        self.assertEqual(1, total)
        self.assertEqual(n1["id"], ns[0]["id"])

        ns, total = models.search.user_node(self.uid)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        code = models.node.restore_from_trash(self.uid, n1["id"])
        self.assertEqual(const.Code.OK, code)
        nodes, total = models.search.user_node(self.uid)
        self.assertEqual(4, len(nodes))
        self.assertEqual(4, total)

    def test_search(self):
        code = models.search.put_recent_search(self.uid, "a")
        self.assertEqual(const.Code.OK, code)
        models.search.put_recent_search(self.uid, "c")
        models.search.put_recent_search(self.uid, "b")

        queries = models.search.get_recent_search(self.uid)
        self.assertEqual(["b", "c", "a"], queries)

    def test_batch(self):
        ns = []
        for i in range(10):
            n, code = models.node.add(
                uid=self.uid, md=f"title{i}\ntext", type_=const.NodeType.MARKDOWN.value
            )
            self.assertEqual(const.Code.OK, code)
            ns.append(n)

        base_count = 2

        code = models.node.batch_to_trash(self.uid, [n["id"] for n in ns[:4]])
        self.assertEqual(const.Code.OK, code)
        nodes, total = models.search.user_node(self.uid)
        self.assertEqual(6 + base_count, len(nodes))
        self.assertEqual(6 + base_count, total)

        tns, total = models.node.get_nodes_in_trash(self.uid, 0, 10)
        self.assertEqual(4, total)
        self.assertEqual(4, len(tns))

        code = models.node.restore_batch_from_trash(self.uid, [n["id"] for n in tns[:2]])
        self.assertEqual(const.Code.OK, code)
        nodes, total = models.search.user_node(self.uid)
        self.assertEqual(8 + base_count, len(nodes))
        self.assertEqual(8 + base_count, total)

        code = models.node.batch_delete(self.uid, [n["id"] for n in tns[2:4]])
        self.assertEqual(const.Code.OK, code)
        tns, total = models.node.get_nodes_in_trash(self.uid, 0, 10)
        self.assertEqual(0, total)
        self.assertEqual(0, len(tns))

    def test_files_upload_process(self):
        now = datetime.datetime.now(tz=utc)
        doc: models.tps.ImportData = {
            "_id": ObjectId(),
            "uid": "xxx",
            "process": 0,
            "type": "text",
            "startAt": now,
            "running": True,
            "obsidian": {},
            "problemFiles": [],
            "code": const.Code.OK.value,
        }
        res = models.database.COLL.import_data.insert_one(doc)
        self.assertTrue(res.acknowledged)

        doc, code = models.files.update_process("xxx", "obsidian", 10)
        self.assertEqual(const.Code.OK, code)

        doc = models.files.get_upload_process("xxx")
        self.assertEqual(10, doc["process"])
        self.assertEqual("obsidian", doc["type"])
        self.assertEqual(now, doc["startAt"])
        self.assertTrue(doc["running"])

        models.database.COLL.import_data.delete_one({"uid": "xxx"})

    def test_update_title_and_from_nodes_updates(self):
        n1, code = models.node.add(
            uid=self.uid, md=f"title1\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        n2, code = models.node.add(
            uid=self.uid, md=f"title2\n[@title1](/n/{n1['id']})", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)

        n1, code = models.node.update(uid=self.uid, nid=n1["id"], md="title1Changed\ntext")
        self.assertEqual(const.Code.OK, code)
        n2, code = models.node.get(uid=self.uid, nid=n2["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(f"title2\n[@title1Changed](/n/{n1['id']})", n2["md"])

    def test_upload_image_vditor(self):
        u, code = models.user.get(self.uid)
        used_space = u["usedSpace"]

        p = Path(__file__).parent.parent / "img" / "phone-notes.png"
        image = Image.open(p)
        buf = BytesIO()
        image.save(buf, format="png")
        size = buf.tell()
        img_file = UploadFile(
            buf, filename="phone-notes.png", size=size,
            headers=Headers({"content-type": "image/png"})
        )
        res = models.files.upload_image_vditor(self.uid, [img_file])
        self.assertIn("phone-notes.png", res["succMap"])
        self.assertTrue(".png" in res["succMap"]["phone-notes.png"])
        local_file = Path(__file__).parent / "tmp" / ".data" / os.path.sep.join(
            res["succMap"]["phone-notes.png"].rsplit("/")[-3:])
        self.assertTrue(local_file.exists())
        local_file.unlink()

        u, code = models.user.get(self.uid)
        self.assertEqual(used_space + size, u["usedSpace"])

    def test_fetch_image_vditor(self):
        u, code = models.user.get(self.uid)
        used_space = u["usedSpace"]

        url = "https://rethink.run/favicon.ico"
        new_url, code = models.files.fetch_image_vditor(self.uid, url)
        self.assertEqual(const.Code.OK, code)
        self.assertTrue(new_url.endswith(".ico"))
        self.assertTrue(new_url.startswith("http://127.0.0.1"))
        local_file = Path(__file__).parent / "tmp" / ".data" / os.path.sep.join(new_url.rsplit("/")[-3:])
        self.assertTrue(local_file.exists())
        local_file.unlink()

        u, code = models.user.get(self.uid)
        r = requests.get(url)
        self.assertEqual(used_space + len(r.content), u["usedSpace"])

    def test_update_used_space(self):
        u, code = models.user.get(self.uid)
        base_used_space = u["usedSpace"]
        for delta, value in [
            (100, 100),
            (100, 200),
            (0, 200),
            (-300, 0),
            (20.1, 20.1),
        ]:
            code = models.user.update_used_space(self.uid, delta)
            self.assertEqual(const.Code.OK, code)
            u, code = models.user.get(self.uid)
            self.assertEqual(const.Code.OK, code)
            self.assertAlmostEqual(value, u["usedSpace"] - base_used_space, msg=f"delta: {delta}, value: {value}")
