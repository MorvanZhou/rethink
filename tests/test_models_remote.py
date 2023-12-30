import unittest
from textwrap import dedent

import elastic_transport
import pymongo.errors
from bson import ObjectId

from rethink import const, models, config
from rethink.controllers.auth import register_user
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
            await models.database.drop_all()
            await models.database.init()
            uid, code = await register_user(
                email=const.DEFAULT_USER["email"],
                password=self.default_pwd,
                language=const.Language.EN.value)
            self.assertEqual(const.Code.OK, code)
            self.token = models.utils.jwt_encode(
                exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
                data={"uid": uid, "language": const.Language.EN.value},
            )
            self.uid = uid
        except (
                pymongo.errors.NetworkTimeout,
                pymongo.errors.ServerSelectionTimeoutError,
                elastic_transport.ConnectionError,
                RuntimeError,
        ):
            print("remote test asyncSetUp timeout")
            utils.skip_no_connect.skip = True

    async def asyncTearDown(self) -> None:
        if utils.skip_no_connect.skip:
            print("remote test asyncTearDown skipped")
            return
        try:
            await models.database.drop_all()
        except (
                pymongo.errors.NetworkTimeout,
                pymongo.errors.ServerSelectionTimeoutError,
                elastic_transport.ConnectionError,
                RuntimeError,
        ):
            print("remote test asyncTearDown timeout")
            utils.skip_no_connect.skip = True

    @utils.skip_no_connect
    async def test_user(self):
        if models.database.CLIENT is None: return
        _id, code = await register_user(email="aaa@rethink.run", password="bbb123")
        self.assertNotEqual("", str(_id))
        self.assertEqual(const.Code.OK, code)

        u, code = await models.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("rethink", u["nickname"])
        self.assertIsNotNone(u)

        u, code = await models.user.get(_id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("aaa", u["nickname"])

        u, code = await models.user.update(uid=_id, hashed="1", nickname="2", avatar="3")
        self.assertEqual(const.Code.OK, code)

        u, code = await models.user.get(_id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("1", u["hashed"])
        self.assertEqual("2", u["nickname"])
        self.assertEqual("3", u["avatar"])

        code = await models.user.disable(uid=_id)
        self.assertEqual(const.Code.OK, code)

        u, code = await models.user.get(uid=_id)
        self.assertEqual(const.Code.ACCOUNT_OR_PASSWORD_ERROR, code)

        code = await models.user.enable(uid=_id)
        self.assertEqual(const.Code.OK, code)

        code = await models.user.disable(uid="ssaa")
        self.assertEqual(const.Code.OPERATION_FAILED, code)

        code = await models.user.delete(uid=_id)
        self.assertEqual(const.Code.OK, code)

    @utils.skip_no_connect
    async def test_node(self):
        u, code = await models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        used_space = u["usedSpace"]
        node, code = await models.node.add(
            uid=self.uid, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        u, code = await models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space + len(node["md"].encode("utf-8")), u["usedSpace"])

        n, code = await models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title", n["title"])

        await models.database.searcher().refresh()
        ns, total = await models.database.searcher().search(uid=self.uid)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        u, code = await models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        used_space = u["usedSpace"]
        n, code = await models.node.update(uid=self.uid, nid=node["id"], md="# title2\ntext2")
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title2", n["title"])
        self.assertEqual("text2", n["snippet"])
        self.assertEqual(const.NodeType.MARKDOWN.value, n["type"])

        u, code = await models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space + (
                len(n["md"].encode("utf-8")) -
                len(node["md"].encode("utf-8"))
        ), u["usedSpace"])

        code = await models.node.disable(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        await models.database.searcher().refresh()
        n, code = await models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.NODE_NOT_EXIST, code)

        code = await models.node.to_trash(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        await models.database.searcher().refresh()
        code = await models.node.delete(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        n, code = await models.node.get(uid=self.uid, nid=node["id"])
        self.assertIsNone(n)
        self.assertEqual(const.Code.NODE_NOT_EXIST, code)

        u, code = await models.user.get(self.uid)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(used_space - len(node["md"].encode("utf-8")), u["usedSpace"])

    @utils.skip_no_connect
    async def test_parse_at(self):
        nid1, _ = await models.node.add(
            uid=self.uid, md="c", type_=const.NodeType.MARKDOWN.value,
        )
        nid2, _ = await models.node.add(
            uid=self.uid, md="我133", type_=const.NodeType.MARKDOWN.value,
        )
        md = dedent(
            f"""title
            fffqw [@c](/n/{nid1['id']})
            fff
            [@我133](/n/{nid2['id']})
            ffq
            """)
        node, code = await models.node.add(
            uid=self.uid, md=md, type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        await models.database.searcher().refresh()
        nodes, total = await models.database.searcher().search(uid=self.uid)
        self.assertEqual(5, len(nodes))
        self.assertEqual(5, total)

        found, total = await models.database.searcher().search(uid=self.uid, query="我")
        self.assertEqual(2, len(found), msg=found)
        self.assertEqual(2, total)

        recommend = await models.database.searcher().recommend(
            uid=self.uid,
            content="I do need a Knowledge Management System. This is a good one to try.",
            exclude_nids=[],
        )
        self.assertEqual(1, len(recommend))

        n, code = await models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(2, len(n["toNodeIds"]))

        tmp_text = n["md"]
        n, code = await models.node.update(uid=self.uid, nid=node["id"], md=tmp_text + "xxxx")
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(tmp_text + "xxxx", n["md"])

        n, code = await models.node.get(uid=self.uid, nid=nid1['id'])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(1, len(n["fromNodeIds"]))

        n, code = await models.node.update(uid=self.uid, nid=node["id"], md=n["md"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(0, len(n["toNodeIds"]))

        n, code = await models.node.get(uid=self.uid, nid=nid1['id'])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(0, len(n["fromNodeIds"]))

    @utils.skip_no_connect
    async def test_add_set(self):
        node, code = await models.node.add(
            uid=self.uid, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(0, len(node["toNodeIds"]))
        self.assertEqual(const.Code.OK, code)

        res = await models.db_ops.node_add_to_set(node["id"], "toNodeIds", ObjectId())
        self.assertEqual(1, res.modified_count)
        node, code = await models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(1, len(node["toNodeIds"]))

    @utils.skip_no_connect
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

        await models.database.searcher().refresh()
        ns, total = await models.database.searcher().search(self.uid)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        code = await models.node.restore_from_trash(self.uid, n1["id"])
        self.assertEqual(const.Code.OK, code)

        await models.database.searcher().refresh()
        nodes, total = await models.database.searcher().search(self.uid)
        self.assertEqual(4, len(nodes))
        self.assertEqual(4, total)

    @utils.skip_no_connect
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

        await models.database.searcher().refresh()
        nodes, total = await models.database.searcher().search(self.uid)
        self.assertEqual(6 + base_count, len(nodes))
        self.assertEqual(6 + base_count, total)

        tns, total = await models.node.get_nodes_in_trash(self.uid, 0, 10)
        self.assertEqual(4, total)
        self.assertEqual(4, len(tns))

        code = await models.node.restore_batch_from_trash(self.uid, [n["id"] for n in tns[:2]])
        self.assertEqual(const.Code.OK, code)

        await models.database.searcher().refresh()
        nodes, total = await models.database.searcher().search(self.uid)
        self.assertEqual(8 + base_count, len(nodes))
        self.assertEqual(8 + base_count, total)

        code = await models.node.batch_delete(self.uid, [n["id"] for n in tns[2:4]])
        self.assertEqual(const.Code.OK, code)

        tns, total = await models.node.get_nodes_in_trash(self.uid, 0, 10)
        self.assertEqual(0, total)
        self.assertEqual(0, len(tns))

    @utils.skip_no_connect
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
            self.assertEqual(const.Code.OK, code, msg=f"delta: {delta}, value: {value}")
            u, code = await models.user.get(self.uid)
            self.assertEqual(const.Code.OK, code)
            now = u["usedSpace"] - base_used_space
            if now < 0:
                now = 0
                base_used_space = 0
            self.assertAlmostEqual(value, now, msg=f"delta: {delta}, value: {value}")
