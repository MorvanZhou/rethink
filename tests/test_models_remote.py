import unittest

from bson import ObjectId

from rethink import const, models, config
from rethink.controllers.auth import register_user
from . import utils


class RemoteModelsTest(unittest.TestCase):
    default_pwd = "rethink123"

    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.development")
        models.database.drop_all()

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.development")

    def setUp(self) -> None:
        models.database.init()
        uid, code = register_user(
            email=const.DEFAULT_USER["email"],
            password=self.default_pwd,
            language=const.Language.EN.value)
        self.assertEqual(const.Code.OK, code)
        self.token = models.utils.jwt_encode(
            exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
            data={"uid": uid, "language": const.Language.EN.value},
        )
        self.uid = uid

    def tearDown(self) -> None:
        models.database.drop_all()

    def test_user(self):
        _id, code = register_user(email="aaa", password="bbb123")
        self.assertNotEqual("", str(_id))
        self.assertEqual(const.Code.OK, code)

        u, code = models.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("rethink", u["nickname"])
        self.assertIsNotNone(u)

        u, code = models.user.get(_id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("aaa", u["nickname"])

        u, code = models.user.update(uid=_id, email="a@a.com", hashed="1", nickname="2", avatar="3")
        self.assertEqual(const.Code.OK, code)

        u, code = models.user.get(_id)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("a@a.com", u["email"])
        self.assertEqual("1", u["hashed"])
        self.assertEqual("2", u["nickname"])
        self.assertEqual("3", u["avatar"])

        code = models.user.disable(uid=_id)
        self.assertEqual(const.Code.OK, code)

        u, code = models.user.get(uid=_id)
        self.assertEqual(const.Code.ACCOUNT_OR_PASSWORD_ERROR, code)

        code = models.user.enable(uid=_id)
        self.assertEqual(const.Code.OK, code)

        code = models.user.disable(uid="ssaa")
        self.assertEqual(const.Code.OPERATION_FAILED, code)

        code = models.user.delete(uid=_id)
        self.assertEqual(const.Code.OK, code)

    def test_node(self):
        node, code = models.node.add(
            uid=self.uid, title="title", text="text", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)

        n, code = models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title", n["title"])

        ns, total = models.search.user_node(uid=self.uid)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        n, code = models.node.update(uid=self.uid, nid=node["id"], title="title2", text="text2")
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title2", n["title"])
        self.assertEqual("text2", n["text"])
        self.assertEqual(1, n["type"])

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

    def test_parse_at(self):
        nid1, _ = models.node.add(
            uid=self.uid, title="c", text="", type_=const.NodeType.MARKDOWN.value,
        )
        nid2, _ = models.node.add(
            uid=self.uid, title="我133", text="", type_=const.NodeType.MARKDOWN.value,
        )
        text = f"""
        fffqw [@c](/n/{nid1['id']})
        fff 
        [@我133](/n/{nid2['id']})
        ffq
        """
        node, code = models.node.add(
            uid=self.uid, title="title", text=text, type_=const.NodeType.MARKDOWN.value
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

        tmp_text = n["text"]
        n, code = models.node.update(uid=self.uid, nid=node["id"], text=tmp_text + "xxxx", title=n["title"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(tmp_text + "xxxx", n["text"])

        n, code = models.node.get(uid=self.uid, nid=nid1['id'])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(1, len(n["fromNodeIds"]))

        n, code = models.node.update(uid=self.uid, nid=node["id"], text="", title=n["title"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(0, len(n["toNodeIds"]))

        n, code = models.node.get(uid=self.uid, nid=nid1['id'])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(0, len(n["fromNodeIds"]))

    def test_add_set(self):
        node, code = models.node.add(
            uid=self.uid, title="title", text="text", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(0, len(node["toNodeIds"]))
        self.assertEqual(const.Code.OK, code)

        res = models.db_ops.node_add_to_set(node["id"], "toNodeIds", ObjectId())
        self.assertEqual(1, res.modified_count)
        node, code = models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(1, len(node["toNodeIds"]))

    def test_to_trash(self):
        n1, code = models.node.add(
            uid=self.uid, title="title", text="text", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        n2, code = models.node.add(
            uid=self.uid, title="title2", text="text", type_=const.NodeType.MARKDOWN.value
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
