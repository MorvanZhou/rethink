import time
import unittest
from textwrap import dedent
from unittest.mock import patch

import elastic_transport
import pymongo.errors
from bson import ObjectId

from retk import const, config, core
from retk.controllers.schemas.user import PatchUserRequest
from retk.core.account.manager import signup
from retk.models import db_ops
from retk.models.client import client
from retk.models.tps import AuthedUser, convert_user_dict_to_authed_user
from retk.utils import jwt_encode
from . import utils


class RemoteModelsTest(unittest.IsolatedAsyncioTestCase):
    default_pwd = "rethink123"

    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.development")

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.development")

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
                language=const.Language.EN.value)
            self.assertEqual(const.Code.OK, code)
            self.token = jwt_encode(
                exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
                data={"uid": u["id"], "language": const.Language.EN.value},
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
                    "nodeDisplayMethod": const.NodeDisplayMethod.CARD.value,
                    "nodeDisplaySortKey": "modifiedAt"
                },
                "settings": {
                    "language": "en",
                    "editorMode": const.EditorMode.WYSIWYG.value,
                    "editorTheme": const.AppTheme.LIGHT.value,
                    "editorFontSize": 15,
                    "editorCodeTheme": const.EditorCodeTheme.GITHUB.value,
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
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("rethink", u["nickname"])
        self.assertIsNotNone(u)

        u, code = await signup(email="aaa@rethink.run", password="bbb123")
        _id = u["id"]
        self.assertNotEqual("", _id)
        self.assertEqual(const.Code.OK, code)

        u, code = await core.user.get(_id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("aaa", u["nickname"])

        u, code = await core.user.patch(
            au=AuthedUser(
                u=convert_user_dict_to_authed_user(u),
                request_id="xxx",
                language=const.Language.EN.value,
            ),
            req=PatchUserRequest(
                nickname="2",
                avatar="3",
                lastState=PatchUserRequest.LastState(
                    nodeDisplayMethod=const.NodeDisplayMethod.LIST.value,
                )
            )
        )
        self.assertEqual(const.Code.OK, code)

        u, code = await core.user.get(_id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("2", u["nickname"])
        self.assertEqual("3", u["avatar"])

        code = await core.user.disable(uid=_id)
        self.assertEqual(const.Code.OK, code)

        u, code = await core.user.get(uid=_id)
        self.assertEqual(const.Code.ACCOUNT_OR_PASSWORD_ERROR, code)

        code = await core.user.enable(uid=_id)
        self.assertEqual(const.Code.OK, code)

        code = await core.user.disable(uid="ssaa")
        self.assertEqual(const.Code.OPERATION_FAILED, code)

        code = await core.user.delete(uid=_id)
        self.assertEqual(const.Code.OK, code)

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
        mock_save_md_to_cos.return_value = const.Code.OK
        mock_get_md_from_cos.return_value = ("", const.Code.OK)
        mock_remove_md_from_cos.return_value = const.Code.OK
        mock_remove_md_all_versions_from_cos.return_value = const.Code.OK

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.Code.OK, code)
        used_space = u["usedSpace"]
        node, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space + len(node["md"].encode("utf-8")), u["usedSpace"])

        n, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title", n["title"])

        await client.search.refresh()
        ns, total = await client.search.search(au=self.au)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.Code.OK, code)
        used_space = u["usedSpace"]
        n, _, code = await core.node.update_md(au=self.au, nid=node["id"], md="# title2\ntext2")
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title2", n["title"])
        self.assertEqual("text2", n["snippet"])
        self.assertEqual(const.NodeType.MARKDOWN.value, n["type"])

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space + (
                len(n["md"].encode("utf-8")) -
                len(node["md"].encode("utf-8"))
        ), u["usedSpace"])

        code = await core.node.disable(au=self.au, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        await client.search.refresh()
        n, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.Code.NODE_NOT_EXIST, code)

        code = await core.node.to_trash(au=self.au, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        await client.search.refresh()
        code = await core.node.delete(au=self.au, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        n, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertIsNone(n)
        self.assertEqual(const.Code.NODE_NOT_EXIST, code)

        u, code = await core.user.get(self.au.u.id)
        self.assertEqual(const.Code.OK, code)
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
        mock_save_md_to_cos.return_value = const.Code.OK
        mock_get_md_from_cos.return_value = ("", const.Code.OK)
        mock_remove_md_from_cos.return_value = const.Code.OK
        mock_remove_md_all_versions_from_cos.return_value = const.Code.OK

        nid1, _ = await core.node.post(
            au=self.au, md="c", type_=const.NodeType.MARKDOWN.value,
        )
        nid2, _ = await core.node.post(
            au=self.au, md="我133", type_=const.NodeType.MARKDOWN.value,
        )
        md = dedent(
            f"""title
            fffqw [@c](/n/{nid1['id']})
            fff
            [@我133](/n/{nid2['id']})
            ffq
            """)
        node, code = await core.node.post(
            au=self.au, md=md, type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
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
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(2, len(n["toNodeIds"]))

        tmp_text = n["md"]
        n, _, code = await core.node.update_md(au=self.au, nid=node["id"], md=tmp_text + "xxxx")
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(tmp_text + "xxxx", n["md"])

        n, code = await core.node.get(au=self.au, nid=nid1['id'])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(1, len(n["fromNodeIds"]))

        n, _, code = await core.node.update_md(au=self.au, nid=node["id"], md=n["md"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(0, len(n["toNodeIds"]))

        n, code = await core.node.get(au=self.au, nid=nid1['id'])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(0, len(n["fromNodeIds"]))

    @utils.skip_no_connect
    async def test_add_set(self):
        node, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(0, len(node["toNodeIds"]))
        self.assertEqual(const.Code.OK, code)

        res = await db_ops.node_add_to_set(node["id"], "toNodeIds", ObjectId())
        self.assertEqual(1, res.modified_count)
        node, code = await core.node.get(au=self.au, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(1, len(node["toNodeIds"]))

    @utils.skip_no_connect
    async def test_to_trash(self):
        n1, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        n2, code = await core.node.post(
            au=self.au, md="title2\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)

        code = await core.node.to_trash(self.au, n1["id"])
        self.assertEqual(const.Code.OK, code)

        ns, total = await core.node.get_nodes_in_trash(au=self.au, page=0, limit=10)
        self.assertEqual(1, len(ns))
        self.assertEqual(1, total)
        self.assertEqual(n1["id"], ns[0]["id"])

        await client.search.refresh()
        ns, total = await client.search.search(self.au)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        code = await core.node.restore_from_trash(self.au, n1["id"])
        self.assertEqual(const.Code.OK, code)

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
        mock_save_md_to_cos.return_value = const.Code.OK
        mock_get_md_from_cos.return_value = ("", const.Code.OK)
        mock_remove_md_from_cos.return_value = const.Code.OK
        mock_remove_md_all_versions_from_cos.return_value = const.Code.OK
        ns = []
        for i in range(10):
            n, code = await core.node.post(
                au=self.au, md=f"title{i}\ntext", type_=const.NodeType.MARKDOWN.value
            )
            self.assertEqual(const.Code.OK, code)
            ns.append(n)

        base_count = 2

        code = await core.node.batch_to_trash(self.au, [n["id"] for n in ns[:4]])
        self.assertEqual(const.Code.OK, code)

        await client.search.refresh()
        nodes, total = await client.search.search(self.au)
        self.assertEqual(6 + base_count, len(nodes))
        self.assertEqual(6 + base_count, total)

        tns, total = await core.node.get_nodes_in_trash(au=self.au, page=0, limit=10)
        self.assertEqual(4, total)
        self.assertEqual(4, len(tns))

        code = await core.node.restore_batch_from_trash(self.au, [n["id"] for n in tns[:2]])
        self.assertEqual(const.Code.OK, code)

        await client.search.refresh()
        nodes, total = await client.search.search(self.au)
        self.assertEqual(8 + base_count, len(nodes))
        self.assertEqual(8 + base_count, total)

        code = await core.node.batch_delete(self.au, [n["id"] for n in tns[2:4]])
        self.assertEqual(const.Code.OK, code)

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
            self.assertEqual(const.Code.OK, code, msg=f"delta: {delta}, value: {value}")
            u, code = await core.user.get(self.au.u.id)
            self.assertEqual(const.Code.OK, code)
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
        mock_save_md_to_cos.return_value = const.Code.OK
        mock_get_md_from_cos.return_value = ("title2\ntext", const.Code.OK)
        mock_remove_md_from_cos.return_value = const.Code.OK
        mock_remove_md_all_versions_from_cos.return_value = const.Code.OK

        bi = config.get_settings().MD_BACKUP_INTERVAL
        config.get_settings().MD_BACKUP_INTERVAL = 0.0001
        n1, code = await core.node.post(
            au=self.au, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        time.sleep(0.001)

        n2, old_n, code = await core.node.update_md(
            au=self.au, nid=n1["id"], md="title2\ntext",
        )
        self.assertEqual(const.Code.OK, code)
        time.sleep(0.001)

        n2, old_n, code = await core.node.update_md(
            au=self.au, nid=n1["id"], md="title3\ntext",
        )
        self.assertEqual(const.Code.OK, code)

        hist, code = await core.node.get_hist_editions(
            au=self.au,
            nid=n1["id"],
        )
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(2, len(hist))

        hist_md, code = await core.node.get_hist_edition_md(
            au=self.au,
            nid=n1["id"],
            version=hist[1],
        )
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title2\ntext", hist_md)

        config.get_settings().MD_BACKUP_INTERVAL = bi
