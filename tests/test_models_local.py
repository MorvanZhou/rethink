import unittest
from textwrap import dedent

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
        self.assertEqual(const.NodeDisplayMethod.LIST.value, u["nodeDisplayMethod"])

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

        node, code = models.node.add(
            uid=self.uid, md="[title](/qqq)\nbody", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)

        n, code = models.node.get(uid=self.uid, nid=node["id"])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title", n["title"])
        self.assertEqual("body", n["snippet"])

        ns, total = models.search.user_node(uid=self.uid)
        self.assertEqual(3, len(ns))
        self.assertEqual(3, total)

        n, code = models.node.update(uid=self.uid, nid=node["id"], md="title2\nbody2")
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(const.Code.OK, code)
        self.assertEqual("title2", n["title"])
        self.assertEqual("title2\nbody2", n["md"])
        self.assertEqual(const.NodeType.MARKDOWN.value, n["type"])

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
        self.assertEqual(const.Code.NODE_NOT_EXIST, code)

        n1, code = models.node.add(
            uid=self.uid, md="title\ntext", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(const.Code.OK, code)
        code = models.search.put_recent_search(self.uid, n1["id"])
        self.assertEqual(const.Code.OK, code)

        nodes = models.search.get_recent_search(self.uid)
        self.assertEqual(1, len(nodes))
        self.assertEqual(n1["id"], nodes[0]["id"])

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

        code = models.node.batch_delete(self.uid, [n["id"] for n in ns[2:4]])
        self.assertEqual(const.Code.OK, code)
        tns, total = models.node.get_nodes_in_trash(self.uid, 0, 10)
        self.assertEqual(0, total)
        self.assertEqual(0, len(tns))
