import datetime
import time
import unittest
from copy import deepcopy
from textwrap import dedent
from unittest.mock import patch

import elastic_transport
import pymongo.errors
from bson import ObjectId

from retk import const, config, core
from retk.controllers.schemas.user import PatchUserRequest
from retk.core.account.manager import signup
from retk.core.scheduler import tasks
from retk.models import db_ops
from retk.models.client import client
from retk.models.tps import AuthedUser, convert_user_dict_to_authed_user
from retk.utils import get_token
from . import utils


class RemoteModelsTest(unittest.IsolatedAsyncioTestCase):
    default_pwd = "rethink123"

    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.dev")

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.dev")

    async def asyncSetUp(self) -> None:
        if utils.skip_no_connect.skip:
            print("remote test asyncSetUp skipped")
            return

        try:
            client.connection_timeout = 1
            await client.init()
            for coll in client.coll.__dict__.values():
                await coll.delete_many({})

            u, code = await signup(
                email=const.DEFAULT_USER["email"],
                password=self.default_pwd,
                language=const.LanguageEnum.EN.value)
            self.assertEqual(const.CodeEnum.OK, code)
            self.access_token, self.refresh_token = get_token(
                uid=u["id"],
                language=const.LanguageEnum.EN.value,
            )

            self.au = AuthedUser(
                u=convert_user_dict_to_authed_user(u),
                request_id="xxx",
                language=u["settings"]["language"],
            )
        except (
                pymongo.errors.NetworkTimeout,
                pymongo.errors.ServerSelectionTimeoutError,
                elastic_transport.ConnectionError,
        ):
            try:
                await client.drop()
            except pymongo.errors.ServerSelectionTimeoutError:
                pass
            print("remote test asyncSetUp timeout")
            utils.skip_no_connect.skip = True

    async def asyncTearDown(self) -> None:
        if utils.skip_no_connect.skip:
            print("remote test asyncTearDown skipped")
            return
        try:
            await client.drop()
        except (
                pymongo.errors.NetworkTimeout,
                pymongo.errors.ServerSelectionTimeoutError,
                elastic_transport.ConnectionError,
                RuntimeError,
        ):
            print("remote test asyncTearDown timeout")
            utils.skip_no_connect.skip = True

    @utils.skip_no_connect
    async def test_same_key(self):
        async def add():
            oid = ObjectId()
            await client.coll.users.insert_one({
                "_id": oid,
                "id": "same",
                "account": "a",
                "source": 0,
                "email": "email",
                "hashed": "hashed",
                "avatar": "avatar",
                "disabled": False,
                "nickname": "nickname",
                "modifiedAt": oid.generation_time,
                "nodeIds": [],
                "usedSpace": 0,
                "type": const.USER_TYPE.NORMAL.id,
                "lastState": {
                    "recentCursorSearchSelectedNIds": [],
                    "recentSearch": [],
                    "nodeDisplayMethod": const.NodeDisplayMethodEnum.CARD.value,
                    "nodeDisplaySortKey": "modifiedAt"
                },
                "settings": {
                    "language": "en",
                    "editorMode": const.app.EditorModeEnum.WYSIWYG.value,
                    "editorTheme": const.app.AppThemeEnum.LIGHT.value,
                    "editorFontSize": 15,
                    "editorCodeTheme": const.app.EditorCodeThemeEnum.GITHUB.value,
                }
            })
            us = await client.coll.users.find({"id": "same"}).to_list(length=2)
            self.assertIsNotNone(us)
            self.assertEqual(1, len(us))
            self.assertEqual("a", us[0]["account"])

        await add()
        with self.assertRaises(pymongo.errors.DuplicateKeyError):
            await add()

    @utils.skip_no_connect
    async def test_user(self):
        u, code = await core.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("rethink", u["nickname"])
        self.assertIsNotNone(u)

        u, code = await signup(email="aaa@rethink.run", password="bbb123")
        _id = u["id"]
        self.assertNotEqual("", _id)
        self.assertEqual(const.CodeEnum.OK, code)

        u, code = await core.user.get(_id)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("aaa", u["nickname"])

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

        u, code = await core.user.get(_id)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("2", u["nickname"])
        self.assertEqual("3", u["avatar"])

        code = await core.account.manager.disable_by_uid(uid=_id)
        self.assertEqual(const.CodeEnum.OK, code)

        u, code = await core.user.get(uid=_id, disabled=False)
        self.assertEqual(const.CodeEnum.USER_NOT_EXIST, code)

        u, code = await core.user.get(uid=_id, disabled=None)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertTrue(u["disabled"])

        code = await core.account.manager.enable_by_uid(uid=_id)
        self.assertEqual(const.CodeEnum.OK, code)

        code = await core.account.manager.disable_by_uid(uid="ssaa")
        self.assertEqual(const.CodeEnum.USER_NOT_EXIST, code)

        await core.account.manager.delete_by_uid(uid=_id)

    @utils.skip_no_connect
    @patch("retk.core.node.backup.__remove_md_all_versions_from_cos")
    @patch("retk.core.node.backup.__remove_md_from_cos")
    @patch("retk.core.node.backup.__get_md_from_cos")
    @patch("retk.core.node.backup.__save_md_to_cos")
    async def test_node(
            self,
            mock_save_md_to_cos,
            mock_get_md_from_cos,
            mock_remove_md_from_cos,
            mock_remove_md_all_versions_from_cos,
    ):
        mock_save_md_to_cos.return_value = const.CodeEnum.OK
        mock_get_md_from_cos.return_value = ("", const.CodeEnum.OK)
        mock_remove_md_from_cos.return_value = const.CodeEnum.OK
        mock_remove_md_all_versions_from_cos.return_value = const.CodeEnum.OK

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.CodeEnum.OK, code)
        used_space = u["usedSpace"]
        node, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)
        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(used_space + len(node["md"].encode("utf-8")), u["usedSpace"])

        n, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("title", n["title"])

        await client.search.refresh()
        ns, total = await client.search.search(au=self.au)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.CodeEnum.OK, code)
        used_space = u["usedSpace"]
        n, _, code = await core.node.update_md(au=self.au, nid=node["id"], md="# title2\ntext2")
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual("title2", n["title"])
        self.assertEqual("text2", n["snippet"])
        self.assertEqual(const.NodeTypeEnum.MARKDOWN.value, n["type"])

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(used_space + (
                len(n["md"].encode("utf-8")) -
                len(node["md"].encode("utf-8"))
        ), u["usedSpace"])

        code = await core.node.disable(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        await client.search.refresh()
        n, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.NODE_NOT_EXIST, code)

        code = await core.node.to_trash(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        await client.search.refresh()
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

    @utils.skip_no_connect
    @patch("retk.core.node.backup.__remove_md_all_versions_from_cos")
    @patch("retk.core.node.backup.__remove_md_from_cos")
    @patch("retk.core.node.backup.__get_md_from_cos")
    @patch("retk.core.node.backup.__save_md_to_cos")
    async def test_parse_at(
            self,
            mock_save_md_to_cos,
            mock_get_md_from_cos,
            mock_remove_md_from_cos,
            mock_remove_md_all_versions_from_cos,
    ):
        mock_save_md_to_cos.return_value = const.CodeEnum.OK
        mock_get_md_from_cos.return_value = ("", const.CodeEnum.OK)
        mock_remove_md_from_cos.return_value = const.CodeEnum.OK
        mock_remove_md_all_versions_from_cos.return_value = const.CodeEnum.OK

        nid1, _ = await core.node.post(
            au=self.au, md="c", type_=const.NodeTypeEnum.MARKDOWN.value,
        )
        nid2, _ = await core.node.post(
            au=self.au, md="我133", type_=const.NodeTypeEnum.MARKDOWN.value,
        )
        md = dedent(
            f"""title
            fffqw [@c](/n/{nid1['id']})
            fff
            [@我133](/n/{nid2['id']})
            ffq
            """)
        node, code = await core.node.post(
            au=self.au, md=md, type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)
        await client.search.refresh()
        nodes, total = await client.search.search(au=self.au)
        self.assertEqual(5, len(nodes))
        self.assertEqual(5, total)

        found, total = await client.search.search(au=self.au, query="我")
        self.assertEqual(2, len(found), msg=found)
        self.assertEqual(2, total)

        recommend = await client.search.recommend(
            au=self.au,
            content="I do need a Knowledge Management System. This is a good one to try.",
            exclude_nids=[],
        )
        self.assertEqual(1, len(recommend))

        n, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(2, len(n["toNodeIds"]))

        tmp_text = n["md"]
        n, _, code = await core.node.update_md(au=self.au, nid=node["id"], md=tmp_text + "xxxx")
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(tmp_text + "xxxx", n["md"])

        n, code = await core.node.get(au=self.au, nid=nid1['id'])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(1, len(n["fromNodeIds"]))

        n, _, code = await core.node.update_md(au=self.au, nid=node["id"], md=n["md"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(0, len(n["toNodeIds"]))

        n, code = await core.node.get(au=self.au, nid=nid1['id'])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(0, len(n["fromNodeIds"]))

    @utils.skip_no_connect
    async def test_add_set(self):
        node, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(0, len(node["toNodeIds"]))
        self.assertEqual(const.CodeEnum.OK, code)

        res = await db_ops.node_add_to_set(node["id"], "toNodeIds", ObjectId())
        self.assertEqual(1, res.modified_count)
        node, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(1, len(node["toNodeIds"]))

    @utils.skip_no_connect
    async def test_to_trash(self):
        n1, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)
        _, code = await core.node.post(
            au=self.au, md="title2\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
        )
        self.assertEqual(const.CodeEnum.OK, code)

        code = await core.node.to_trash(self.au, n1["id"])
        self.assertEqual(const.CodeEnum.OK, code)

        ns, total = await core.node.get_nodes_in_trash(au=self.au, page=0, limit=10)
        self.assertEqual(1, len(ns))
        self.assertEqual(1, total)
        self.assertEqual(n1["id"], ns[0]["id"])

        await client.search.refresh()
        ns, total = await client.search.search(self.au)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        code = await core.node.restore_from_trash(self.au, n1["id"])
        self.assertEqual(const.CodeEnum.OK, code)

        await client.search.refresh()
        nodes, total = await client.search.search(self.au)
        self.assertEqual(4, len(nodes))
        self.assertEqual(4, total)

    @utils.skip_no_connect
    @patch("retk.core.node.backup.__remove_md_all_versions_from_cos")
    @patch("retk.core.node.backup.__remove_md_from_cos")
    @patch("retk.core.node.backup.__get_md_from_cos")
    @patch("retk.core.node.backup.__save_md_to_cos")
    async def test_batch(
            self,
            mock_save_md_to_cos,
            mock_get_md_from_cos,
            mock_remove_md_from_cos,
            mock_remove_md_all_versions_from_cos,
    ):
        mock_save_md_to_cos.return_value = const.CodeEnum.OK
        mock_get_md_from_cos.return_value = ("", const.CodeEnum.OK)
        mock_remove_md_from_cos.return_value = const.CodeEnum.OK
        mock_remove_md_all_versions_from_cos.return_value = const.CodeEnum.OK
        ns = []
        for i in range(10):
            n, code = await core.node.post(
                au=self.au, md=f"title{i}\ntext", type_=const.NodeTypeEnum.MARKDOWN.value
            )
            self.assertEqual(const.CodeEnum.OK, code)
            ns.append(n)

        base_count = 2

        code = await core.node.batch_to_trash(self.au, [n["id"] for n in ns[:4]])
        self.assertEqual(const.CodeEnum.OK, code)

        await client.search.refresh()
        nodes, total = await client.search.search(self.au)
        self.assertEqual(6 + base_count, len(nodes))
        self.assertEqual(6 + base_count, total)

        tns, total = await core.node.get_nodes_in_trash(au=self.au, page=0, limit=10)
        self.assertEqual(4, total)
        self.assertEqual(4, len(tns))

        code = await core.node.restore_batch_from_trash(self.au, [n["id"] for n in tns[:2]])
        self.assertEqual(const.CodeEnum.OK, code)

        await client.search.refresh()
        nodes, total = await client.search.search(self.au)
        self.assertEqual(8 + base_count, len(nodes))
        self.assertEqual(8 + base_count, total)

        code = await core.node.batch_delete(self.au, [n["id"] for n in tns[2:4]])
        self.assertEqual(const.CodeEnum.OK, code)

        tns, total = await core.node.get_nodes_in_trash(au=self.au, page=0, limit=10)
        self.assertEqual(0, total)
        self.assertEqual(0, len(tns))

    @utils.skip_no_connect
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
            code = await core.user.update_used_space(self.au.u.id, delta)
            self.assertEqual(const.CodeEnum.OK, code, msg=f"delta: {delta}, value: {value}")
            u, code = await core.user.get(self.au.u.id)
            self.assertEqual(const.CodeEnum.OK, code)
            now = u["usedSpace"] - base_used_space
            if now < 0:
                now = 0
                base_used_space = 0
            self.assertAlmostEqual(value, now, msg=f"delta: {delta}, value: {value}")

    @utils.skip_no_connect
    @patch("retk.core.node.backup.__remove_md_all_versions_from_cos")
    @patch("retk.core.node.backup.__remove_md_from_cos")
    @patch("retk.core.node.backup.__get_md_from_cos")
    @patch("retk.core.node.backup.__save_md_to_cos")
    async def test_md_history(
            self,
            mock_save_md_to_cos,
            mock_get_md_from_cos,
            mock_remove_md_from_cos,
            mock_remove_md_all_versions_from_cos,
    ):
        mock_save_md_to_cos.return_value = const.CodeEnum.OK
        mock_get_md_from_cos.return_value = ("title2\ntext", const.CodeEnum.OK)
        mock_remove_md_from_cos.return_value = const.CodeEnum.OK
        mock_remove_md_all_versions_from_cos.return_value = const.CodeEnum.OK

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

    @utils.skip_no_connect
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

    @utils.skip_no_connect
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

    @utils.skip_no_connect
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
