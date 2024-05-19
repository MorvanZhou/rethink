import datetime
import shutil
import time
import unittest
from copy import deepcopy
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

from retk import const, core, config
from retk.controllers.schemas.user import PatchUserRequest
from retk.core.files.importing.async_tasks.utils import update_process
from retk.core.scheduler import tasks
from retk.models import db_ops
from retk.models.client import client
from retk.models.tps import ImportData, AuthedUser, convert_user_dict_to_authed_user
from retk.utils import short_uuid
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
        await client.init()
        u, _ = await core.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.au = AuthedUser(
            u=convert_user_dict_to_authed_user(u),
            request_id="xxx",
            language=u["settings"]["language"],
        )

    async def asyncTearDown(self) -> None:
        await client.drop()
        shutil.rmtree(Path(__file__).parent / "tmp" / const.settings.DOT_DATA / "files", ignore_errors=True)
        shutil.rmtree(Path(__file__).parent / "tmp" / const.settings.DOT_DATA / "md", ignore_errors=True)

    async def test_user(self):
        u, code = await core.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("rethink", u["nickname"])
        self.assertIsNotNone(u)

        u, code = await core.user.add(
            account="aaa", source=const.UserSourceEnum.EMAIL.value,
            email="aaa", hashed="bbb", nickname="ccc", avatar="ddd", language=const.LanguageEnum.EN.value)
        self.assertNotEqual("", u["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        _uid = u["id"]

        u, code = await core.user.get(_uid)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("ccc", u["nickname"])

        u, code = await core.user.patch(
            au=AuthedUser(
                u=convert_user_dict_to_authed_user(u),
                request_id="xxx",
                language=const.LanguageEnum.EN.value,
            ),
            req=PatchUserRequest(
                nickname="2",
                avatar="3",
                lastState=PatchUserRequest.LastState(
                    nodeDisplayMethod=const.NodeDisplayMethodEnum.LIST.value,
                )
            )
        )
        self.assertEqual(const.CodeEnum.OK, code)

        u, code = await core.user.get(_uid)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("bbb", u["hashed"])
        self.assertEqual("2", u["nickname"])
        self.assertEqual("3", u["avatar"])
        self.assertEqual(const.NodeDisplayMethodEnum.LIST.value, u["lastState"]["nodeDisplayMethod"])

        code = await core.account.manager.disable_by_uid(uid=_uid)
        self.assertEqual(const.CodeEnum.OK, code)

        u, code = await core.user.get(uid=_uid)
        self.assertEqual(const.CodeEnum.USER_NOT_EXIST, code)
        self.assertIsNone(u)

        u, code = await core.user.get(uid=_uid, disabled=None)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertTrue(u["disabled"])

        code = await core.account.manager.enable_by_uid(uid=_uid)
        self.assertEqual(const.CodeEnum.OK, code)

        code = await core.account.manager.disable_by_uid(uid="sdwqdqw")
        self.assertEqual(const.CodeEnum.USER_NOT_EXIST, code)

        await core.account.manager.delete_by_uid(uid=_uid)

    async def test_node(self):
        node, code = await core.node.post(
            au=self.au, md="a" * (const.settings.MD_MAX_LENGTH + 1), type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.NOTE_EXCEED_MAX_LENGTH, code)
        self.assertIsNone(node)

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.CodeEnum.OK, code)
        used_space = u["usedSpace"]
        node, code = await core.node.post(
            au=self.au, md="[title](/qqq)\nbody", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)
        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(used_space + len(node["md"].encode("utf-8")), u["usedSpace"])
        self.assertEqual("modifiedAt", u["lastState"]["nodeDisplaySortKey"])

        n, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("title", n["title"])
        self.assertEqual("body", n["snippet"])

        ns, total = await client.search.search(au=self.au)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        ns, total = await client.search.search(au=self.au, limit=5, page=12, sort_key="createdAt")
        self.assertEqual(0, len(ns))
        self.assertEqual(3, total)

        u, code = await core.user.patch(
            au=self.au,
            req=PatchUserRequest(
                lastState=PatchUserRequest.LastState(
                    nodeDisplaySortKey="createdAt",
                )
            )
        )

        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("createdAt", u["lastState"]["nodeDisplaySortKey"])
        used_space = u["usedSpace"]
        n, _, code = await core.node.update_md(au=self.au, nid=node["id"], md="title2\nbody2")
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("title2", n["title"])
        self.assertEqual("title2\nbody2", n["md"])
        self.assertEqual(const.NodeTypeEnum.MARKDOWN.value, n["type"])

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(used_space + (
                len(n["md"].encode("utf-8")) -
                len(node["md"].encode("utf-8"))
        ), u["usedSpace"])

        code = await core.node.disable(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        n, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.NODE_NOT_EXIST, code)

        code = await core.node.to_trash(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)

        code = await core.node.delete(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        n, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertIsNone(n)
        self.assertEqual(const.CodeEnum.NODE_NOT_EXIST, code)

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(used_space - len(node["md"].encode("utf-8")), u["usedSpace"])

        nodes, total = await core.node.core_nodes(au=self.au, page=0, limit=10)
        self.assertEqual(2, len(nodes))
        self.assertEqual(2, total)

    async def test_parse_at(self):
        nid1, _ = await core.node.post(
            au=self.au, md="c", type_=const.NodeTypeEnum.MARKDOWN.value,
        )
        nid2, _ = await core.node.post(
            au=self.au, md="我133", type_=const.NodeTypeEnum.MARKDOWN.value,
        )
        md = dedent(f"""title
        fffqw [@c](/n/{nid1['id']})
        fff
        [@我133](/n/{nid2['id']})
        ffq
        """)
        node, code = await core.node.post(
            au=self.au, md=md, type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)
        nodes, total = await client.search.search(
            au=self.au,
            query="",
            sort_key="createdAt",
            reverse=True,
            page=0,
            limit=10,
            exclude_nids=[],
        )
        self.assertEqual(5, len(nodes))
        self.assertEqual(5, total)
        found, total = await client.search.search(au=self.au, query="我")
        self.assertEqual(2, len(found), msg=found)
        self.assertEqual(2, total)

        n, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(2, len(n["toNodeIds"]))

        cache = n["md"]
        n, _, code = await core.node.update_md(au=self.au, nid=node["id"], md=f'{cache}xxxx')
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(cache + "xxxx", n["md"])

        n, code = await core.node.get(au=self.au, nid=nid1['id'])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(1, len(n["fromNodeIds"]))

        n, _, code = await core.node.update_md(au=self.au, nid=node["id"], md=n["title"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(0, len(n["toNodeIds"]))

        n, code = await core.node.get(au=self.au, nid=nid1['id'])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(0, len(n["fromNodeIds"]))

    async def test_add_set(self):
        node, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(0, len(node["toNodeIds"]))
        self.assertEqual(const.CodeEnum.OK, code)

        res = await db_ops.node_add_to_set(node["id"], "toNodeIds", short_uuid())
        self.assertEqual(1, res.modified_count)
        node, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(1, len(node["toNodeIds"]))

    async def test_cursor_text(self):
        n1, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)
        n2, code = await core.node.post(
            au=self.au, md="title2\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)

        recom, total = await core.node.search.at(
            au=self.au,
            nid=n2["id"],
            query="text",
            page=0,
            limit=10,
        )
        self.assertEqual(1, len(recom))
        self.assertEqual(1, total)

        recom, total = await core.node.search.at(
            au=self.au,
            nid=n2["id"],  # exclude the second node
            query="",  # return recent nodes only
            page=0,
            limit=10,
        )
        self.assertEqual(2, len(recom))
        self.assertEqual(2, total)

        code = await core.recent.added_at_node(au=self.au, nid=n1["id"], to_nid=n2["id"])
        self.assertEqual(const.CodeEnum.OK, code)

        recom, total = await core.node.search.at(
            au=self.au,
            nid=n1["id"],  # exclude the second node
            query="",
            page=0,
            limit=10,
        )
        self.assertEqual(3, len(recom))
        self.assertEqual(3, total)
        self.assertEqual("Welcome to Rethink", recom[2].title)

    async def test_to_trash(self):
        n1, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)
        _, code = await core.node.post(
            au=self.au, md="title2\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)

        code = await core.node.to_trash(au=self.au, nid=n1["id"])
        self.assertEqual(const.CodeEnum.OK, code)

        ns, total = await core.node.get_nodes_in_trash(au=self.au, page=0, limit=10)
        self.assertEqual(1, len(ns))
        self.assertEqual(1, total)
        self.assertEqual(n1["id"], ns[0]["id"])

        ns, total = await client.search.search(au=self.au, query="")
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        code = await core.node.restore_from_trash(au=self.au, nid=n1["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        nodes, total = await client.search.search(au=self.au, query="")
        self.assertEqual(4, len(nodes))
        self.assertEqual(4, total)

    async def test_search(self):
        code = await core.recent.put_recent_search(au=self.au, query="a")
        self.assertEqual(const.CodeEnum.OK, code)
        await core.recent.put_recent_search(au=self.au, query="c")
        await core.recent.put_recent_search(au=self.au, query="b")

        doc = await client.coll.users.find_one({"id": self.au.u.id})
        self.assertIsNotNone(doc)
        self.assertEqual(["b", "c", "a"], doc["lastState"]["recentSearch"])

    async def test_batch(self):
        ns = []
        for i in range(10):
            n, code = await core.node.post(
                au=self.au, md=f"title{i}\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
            )
            self.assertEqual(const.CodeEnum.OK, code)
            ns.append(n)

        base_count = 2

        code = await core.node.batch_to_trash(au=self.au, nids=[n["id"] for n in ns[:4]])
        self.assertEqual(const.CodeEnum.OK, code)
        nodes, total = await client.search.search(au=self.au, query="")
        self.assertEqual(6 + base_count, len(nodes))
        self.assertEqual(6 + base_count, total)

        tns, total = await core.node.get_nodes_in_trash(au=self.au, page=0, limit=10)
        self.assertEqual(4, total)
        self.assertEqual(4, len(tns))

        code = await core.node.restore_batch_from_trash(au=self.au, nids=[n["id"] for n in tns[:2]])
        self.assertEqual(const.CodeEnum.OK, code)
        nodes, total = await client.search.search(au=self.au)
        self.assertEqual(8 + base_count, len(nodes))
        self.assertEqual(8 + base_count, total)

        code = await core.node.batch_delete(au=self.au, nids=[n["id"] for n in tns[2:4]])
        self.assertEqual(const.CodeEnum.OK, code)
        tns, total = await core.node.get_nodes_in_trash(au=self.au, page=0, limit=10)
        self.assertEqual(0, total)
        self.assertEqual(0, len(tns))

    async def test_files_upload_process(self):
        now = datetime.datetime.now(tz=utc)
        doc: ImportData = {
            "_id": ObjectId(),
            "uid": "xxx",
            "process": 0,
            "type": "text",
            "startAt": now,
            "running": True,
            "obsidian": {},
            "msg": "",
            "code": const.CodeEnum.OK.value,
        }
        res = await client.coll.import_data.insert_one(doc)
        self.assertTrue(res.acknowledged)

        doc, code = await update_process("xxx", "obsidian", 10)
        self.assertEqual(const.CodeEnum.OK, code)

        doc = await core.files.get_upload_process("xxx1213")
        self.assertIsNone(doc)

        doc = await core.files.get_upload_process("xxx")
        self.assertEqual(10, doc["process"])
        self.assertEqual("obsidian", doc["type"])
        self.assertEqual(now, doc["startAt"])
        self.assertTrue(doc["running"])

        await client.coll.import_data.delete_one({"uid": "xxx"})

    async def test_update_title_and_from_nodes_updates(self):
        n1, code = await core.node.post(
            au=self.au, md="title1\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)
        n2, code = await core.node.post(
            au=self.au, md=f"title2\n[@title1](/n/{n1['id']})", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)

        n1, _, code = await core.node.update_md(au=self.au, nid=n1["id"], md="title1Changed\ntext")
        self.assertEqual(const.CodeEnum.OK, code)
        n2, code = await core.node.get(au=self.au, nid=n2["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(f"title2\n[@title1Changed](/n/{n1['id']})", n2["md"])

    async def test_upload_image_vditor(self):
        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.CodeEnum.OK, code)
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
        res = await core.files.vditor_upload(au=self.au, files=[img_file])
        self.assertIn("fake.png", res["succMap"])
        self.assertTrue(".png" in res["succMap"]["fake.png"])
        local_file = Path(__file__).parent / "tmp" / const.settings.DOT_DATA / res["succMap"]["fake.png"][1:]
        self.assertTrue(local_file.exists())
        local_file.unlink()
        image.close()
        buf.close()
        await img_file.close()

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(used_space + size, u["usedSpace"])

    @patch(
        "retk.core.files.upload.httpx.AsyncClient.get",
    )
    async def test_fetch_image_vditor(self, mock_get):
        f = open(Path(__file__).parent / "tmp" / "fake.png", "rb")
        mock_get.return_value = httpx.Response(
            200,
            content=f.read(),
            headers={"content-type": "image/png"}
        )

        u, code = await core.user.get(self.au.u.id)
        used_space = u["usedSpace"]

        url = "https://rethink.run/favicon.png"
        new_url, code = await core.files.fetch_image_vditor(au=self.au, url=url)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertTrue(new_url.endswith(".png"))
        self.assertTrue(new_url.startswith("/"))
        local_file = Path(__file__).parent / "tmp" / const.settings.DOT_DATA / new_url[1:]
        self.assertTrue(local_file.exists())
        local_file.unlink()

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(used_space + f.tell(), u["usedSpace"])
        f.close()

    async def test_update_used_space(self):
        u, code = await core.user.get(self.au.u.id)
        base_used_space = u["usedSpace"]
        for delta, value in [
            (100, 100),
            (100, 200),
            (0, 200),
            (-3000, 0),
            (20.1, 20.1),
        ]:
            code = await core.user.update_used_space(uid=self.au.u.id, delta=delta)
            self.assertEqual(const.CodeEnum.OK, code)
            u, code = await core.user.get(self.au.u.id)
            self.assertEqual(const.CodeEnum.OK, code)
            now = u["usedSpace"] - base_used_space
            if now < 0:
                now = 0
                base_used_space = 0
            self.assertAlmostEqual(value, now, msg=f"delta: {delta}, value: {value}")

    async def test_node_version(self):
        node, code = await core.node.post(
            au=self.au, md="[title](/qqq)\nbody", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)
        md_path = Path(__file__).parent / "tmp" / const.settings.DOT_DATA / "md" / (node["id"] + ".md")
        self.assertTrue(md_path.exists())

        time.sleep(1)

        _, _, code = await core.node.update_md(au=self.au, nid=node["id"], md="title2\nbody2")
        self.assertEqual(const.CodeEnum.OK, code)
        hist_dir = Path(__file__).parent / "tmp" / const.settings.DOT_DATA / "md" / "hist" / node["id"]
        self.assertEqual(1, len(list(hist_dir.glob("*.md"))))

        time.sleep(1)

        _, _, code = await core.node.update_md(au=self.au, nid=node["id"], md="title2\nbody3")
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(2, len(list(hist_dir.glob("*.md"))))

    async def test_md_history(self):
        bi = config.get_settings().MD_BACKUP_INTERVAL
        config.get_settings().MD_BACKUP_INTERVAL = 0.0001
        n1, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)
        time.sleep(0.001)

        _, _, code = await core.node.update_md(
            au=self.au, nid=n1["id"], md="title2\ntext",
        )
        self.assertEqual(const.CodeEnum.OK, code)
        time.sleep(0.001)

        _, _, code = await core.node.update_md(
            au=self.au, nid=n1["id"], md="title3\ntext",
        )
        self.assertEqual(const.CodeEnum.OK, code)

        hist, code = await core.node.get_hist_editions(
            au=self.au,
            nid=n1["id"],
        )
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(2, len(hist))

        hist_md, code = await core.node.get_hist_edition_md(
            au=self.au,
            nid=n1["id"],
            version=hist[1],
        )
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("title2\ntext", hist_md)

        config.get_settings().MD_BACKUP_INTERVAL = bi

    async def test_get_version(self):
        v, code = await core.self_hosted.get_latest_pkg_version()
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(3, len(v))
        for num in v:
            self.assertTrue(isinstance(num, int))

    async def test_system_notice(self):
        au = deepcopy(self.au)
        au.u.type = const.USER_TYPE.MANAGER.id
        publish_at = datetime.datetime.now()
        doc, code = await core.notice.post_in_manager_delivery(
            au=au,
            title="title",
            content="content",
            recipient_type=const.notice.RecipientTypeEnum.ALL.value,
            batch_type_ids=[],
            publish_at=publish_at,
        )
        self.assertEqual(const.CodeEnum.OK, code)

        docs, total = await core.notice.get_system_notices(0, 10)
        self.assertEqual(1, len(docs))
        self.assertEqual(1, total)
        self.assertEqual(doc["_id"], docs[0]["_id"])
        self.assertEqual("title", docs[0]["title"])
        self.assertEqual("content", docs[0]["snippet"])
        self.assertEqual(publish_at.second, docs[0]["publishAt"].second)
        self.assertFalse(docs[0]["scheduled"])

        await tasks.notice.async_deliver_unscheduled_system_notices()
        time.sleep(0.01)
        docs, total = await core.notice.get_system_notices(0, 10)
        self.assertTrue(docs[0]["scheduled"])

    async def test_notice(self):
        au = deepcopy(self.au)
        doc, code = await core.notice.post_in_manager_delivery(
            au=au,
            title="title",
            content="content",
            recipient_type=const.notice.RecipientTypeEnum.ALL.value,
            batch_type_ids=[],
            publish_at=None,
        )
        self.assertEqual(const.CodeEnum.NOT_PERMITTED, code)

        au.u.type = const.USER_TYPE.MANAGER.id
        doc, code = await core.notice.post_in_manager_delivery(
            au=au,
            title="title",
            content="content",
            recipient_type=const.notice.RecipientTypeEnum.ALL.value,
            batch_type_ids=[],
            publish_at=None,
        )
        self.assertEqual(const.CodeEnum.OK, code)

        await tasks.notice.async_deliver_unscheduled_system_notices()

        res = await client.coll.notice_system.find().to_list(None)
        self.assertEqual(1, len(res))
        self.assertEqual(doc["_id"], res[0]["noticeId"])
        self.assertEqual(au.u.id, res[0]["senderId"])
        self.assertFalse(res[0]["read"])

        d = await client.coll.notice_manager_delivery.find_one({"_id": doc["_id"]})
        self.assertIsNotNone(d)
        self.assertTrue(d["scheduled"])

        n, code = await core.notice.get_user_notices(au)
        self.assertEqual(const.CodeEnum.OK, code)
        sn = n["system"]["notices"]
        self.assertEqual(1, len(sn))
        self.assertEqual(1, n["system"]["total"])
        self.assertEqual(str(doc["_id"]), sn[0]["id"])
        self.assertEqual("title", sn[0]["title"])
        self.assertEqual("content", sn[0]["snippet"])
        self.assertLess(datetime.datetime.strptime(sn[0]["publishAt"], '%Y-%m-%dT%H:%M:%SZ'), datetime.datetime.now())
        self.assertFalse(sn[0]["read"])
        self.assertIsNone(sn[0]["readTime"])

        n, code = await core.notice.get_system_notice(au.u.id, notice_id=str(doc["_id"]))
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("title", n["title"])
        self.assertEqual("<p>content</p>", n["html"])
        self.assertLess(datetime.datetime.strptime(sn[0]["publishAt"], '%Y-%m-%dT%H:%M:%SZ'), datetime.datetime.now())
        self.assertFalse(sn[0]["read"])
        self.assertIsNone(sn[0]["readTime"])

    async def test_mark_read(self):
        au = deepcopy(self.au)
        au.u.type = const.USER_TYPE.MANAGER.id
        for i in range(3):
            _, code = await core.notice.post_in_manager_delivery(
                au=au,
                title=f"title{i}",
                content=f"content{i}",
                recipient_type=const.notice.RecipientTypeEnum.ALL.value,
                batch_type_ids=[],
                publish_at=None,
            )
            self.assertEqual(const.CodeEnum.OK, code)

        await tasks.notice.async_deliver_unscheduled_system_notices()

        au.u.type = const.USER_TYPE.NORMAL.id
        n, code = await core.notice.get_user_notices(au)
        self.assertEqual(const.CodeEnum.OK, code)
        sn = n["system"]["notices"]
        self.assertEqual(3, len(sn))
        self.assertEqual(3, n["system"]["total"])
        for s in sn:
            self.assertFalse(s["read"])
            self.assertIsNone(s["readTime"])

        code = await core.notice.mark_system_notice_read(au.u.id, sn[0]["id"])
        self.assertEqual(const.CodeEnum.OK, code)

        n, code = await core.notice.get_user_notices(au)
        self.assertEqual(const.CodeEnum.OK, code)
        _sn = n["system"]["notices"]
        self.assertEqual(3, len(_sn))
        self.assertEqual(3, n["system"]["total"])
        for i in range(3):
            if _sn[i]["id"] == sn[0]["id"]:
                self.assertTrue(_sn[i]["read"])
                self.assertIsNotNone(_sn[i]["readTime"])
                continue
            self.assertFalse(sn[i]["read"])
            self.assertIsNone(sn[i]["readTime"])

        code = await core.notice.mark_all_system_notice_read(au)
        self.assertEqual(const.CodeEnum.OK, code)

        n, code = await core.notice.get_user_notices(au)
        self.assertEqual(const.CodeEnum.OK, code)
        sn = n["system"]["notices"]
        self.assertEqual(3, len(sn))
        self.assertEqual(3, n["system"]["total"])
        for s in sn:
            self.assertTrue(s["read"])
            self.assertIsNotNone(s["readTime"])
