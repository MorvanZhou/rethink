import datetime
import unittest

from fastapi.testclient import TestClient
from httpx import Response

from rethink import const
from rethink.application import app
from rethink.models import database
from . import utils


class PublicApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")
        database.init()

    def setUp(self) -> None:
        self.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        database.drop_all()
        utils.drop_env(".env.test.local")

    def test_home(self):
        resp = self.client.get("/")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("text/html; charset=utf-8", resp.headers["content-type"])
        self.assertEqual(Response, type(resp))

    def test_register(self):
        resp = self.client.put("/api/user", json={
            "email": "a@c.com",
            "password": "a",
            "language": const.Language.EN.value,
            "requestId": "xxx"
        })
        rj = resp.json()
        self.assertEqual(const.Code.ONE_USER_MODE.value, rj["code"])
        self.assertEqual(len(rj["token"]), 0)
        self.assertEqual("xxx", rj["requestId"])


class TokenApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")
        database.init()
        cls.client = TestClient(app)

    def setUp(self) -> None:
        resp = self.client.post("/api/login", json={
            "email": const.DEFAULT_USER["email"],
            "password": "",
        })
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.token = rj["token"]

    @classmethod
    def tearDownClass(cls) -> None:
        database.drop_all()
        utils.drop_env(".env.test.local")

    def test_get_user(self):
        resp = self.client.get(
            "/api/user",
            params={"rid": "xxx"},
            headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("rethink", rj["user"]["nickname"])
        self.assertEqual("xxx", rj["requestId"])
        self.assertGreater(
            datetime.datetime.strptime(rj["user"]["createdAt"], "%Y-%m-%dT%H:%M:%SZ").timestamp(),
            0., msg=rj["user"]["createdAt"])

    def test_update_user(self):
        resp = self.client.post("/api/user", json={
            "requestId": "xxx",
            "nickname": "new nickname",
            "avatar": "http://new.avatar/aa.png",
        }, headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])

        resp = self.client.get("/api/user", params={"rid": "xxx"}, headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("new nickname", rj["user"]["nickname"])
        self.assertEqual("http://new.avatar/aa.png", rj["user"]["avatar"])
        self.assertEqual("xxx", rj["requestId"])

    def test_node(self):
        resp = self.client.post(
            "/api/search/node",
            json={
                "query": "",
                "requestId": "xxx",
                "sortKey": "createdAt",
                "sortOrder": -1, "page": 0, "pageSize": 5},
            headers={"token": self.token})
        rj = resp.json()
        self.assertGreater(len(rj["data"]["nodes"]), 0)

        self.client.post(
            "/api/search/node",
            json={
                "query": "qqq",
                "requestId": "xxx",
                "sortKey": "createdAt",
                "sortOrder": -1, "page": 0, "pageSize": 5},
            headers={"token": self.token})

        resp = self.client.get(
            "/api/search/recentQueries",
            params={"rid": "xxx"},
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
        self.assertEqual(len(rj["queries"]), 1)
        self.assertEqual(rj["queries"][0], "qqq")

        resp = self.client.put("/api/node", json={
            "requestId": "xxx",
            "fulltext": "node1\ntext",
            "type": const.NodeType.MARKDOWN.value,
        }, headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
        node = rj["node"]

        resp = self.client.get(
            "/api/node",
            params={"rid": "xxx", "nid": node["id"]},
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
        n = rj["node"]
        self.assertEqual("node1", n["title"], msg=rj)
        self.assertEqual("text", n["text"])
        self.assertEqual(const.NodeType.MARKDOWN.value, n["type"])

        resp = self.client.post(
            "/api/node",
            json={
                "requestId": "xxx",
                "nid": node["id"],
                "fulltext": "node2\ntext"
            },
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])

        resp = self.client.get(
            "/api/node",
            params={"rid": "xxx", "nid": node["id"]},
            headers={"token": self.token}
        )
        rj = resp.json()
        n = rj["node"]
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
        self.assertEqual("node2", n["title"])
        self.assertEqual("text", n["text"])
        self.assertEqual(const.NodeType.MARKDOWN.value, n["type"])

        resp = self.client.put(
            "/api/trash",
            json={
                "requestId": "xxx",
                "nid": node["id"],
            },
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])

        resp = self.client.get(
            "/api/trash",
            params={"rid": "xxx", "p": 0, "ps": 10},
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual(1, len(rj["data"]["nodes"]))

        resp = self.client.post(
            "/api/trashRestore",
            json={
                "requestId": "xxx",
                "nid": node["id"],
            },
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])

        self.client.put(
            "/api/trash",
            json={
                "requestId": "xxx",
                "nid": node["id"],
            },
            headers={"token": self.token}
        )
        resp = self.client.delete(
            f"/api/trash/{node['id']}",
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])

        resp = self.client.delete(
            "/api/trash/ssa",
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(const.Code.NODE_NOT_EXIST.value, rj["code"])

        resp = self.client.get(
            "/api/node",
            params={"rid": "xxx", "nid": node["id"]},
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(const.Code.NODE_NOT_EXIST.value, rj["code"])
