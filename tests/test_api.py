import datetime
import unittest

from fastapi.testclient import TestClient
from httpx import Response

from rethink import const
from rethink.application import app
from rethink.models import database
from rethink.models.utils import jwt_decode
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

    def setUp(self) -> None:
        database.init()
        self.client = TestClient(app)
        resp = self.client.post("/api/login", json={
            "email": const.DEFAULT_USER["email"],
            "password": "",
        })
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.token = rj["token"]

    def tearDown(self) -> None:
        database.drop_all()

    @classmethod
    def tearDownClass(cls) -> None:
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
            "nodeDisplayMethod": const.NodeDisplayMethod.LIST.value,
        }, headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])

        resp = self.client.get("/api/user", params={"rid": "xxx"}, headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("new nickname", rj["user"]["nickname"])
        self.assertEqual("http://new.avatar/aa.png", rj["user"]["avatar"])
        self.assertEqual(const.NodeDisplayMethod.LIST.value, rj["user"]["nodeDisplayMethod"])
        self.assertEqual("xxx", rj["requestId"])

    def test_recent_search(self):
        resp = self.client.put("/api/node", json={
            "requestId": "xxx",
            "md": "node1\ntext",
            "type": const.NodeType.MARKDOWN.value,
        }, headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])

        resp = self.client.put(
            "/api/search/recent",
            json={
                "requestId": "xxx",
                "nid": rj["node"]["id"],
            }, headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])

        resp = self.client.get(
            "/api/search/recent",
            params={"rid": "xxx"},
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
        self.assertEqual(len(rj["nodes"]), 1)
        self.assertEqual(rj["nodes"][0]["title"], "node1")

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
                "query": "",
                "requestId": "xxx",
                "sortKey": "createdAt",
                "sortOrder": -1, "page": 0, "pageSize": 5},
            headers={"token": self.token})

        resp = self.client.put("/api/node", json={
            "requestId": "xxx",
            "md": "node1\ntext",
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
        self.assertEqual("node1\ntext", n["md"])
        self.assertEqual(const.NodeType.MARKDOWN.value, n["type"])

        resp = self.client.post(
            "/api/node",
            json={
                "requestId": "xxx",
                "nid": node["id"],
                "md": "node2\ntext"
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
        self.assertEqual("node2\ntext", n["md"])
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

        resp = self.client.post(
            "/api/search/cursor",
            json={
                "requestId": "xxx",
                "nid": node["id"],
                "textBeforeCursor": "How",
            },
            headers={"token": self.token},
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
        self.assertEqual(1, len(rj["nodes"]))
        self.assertEqual("How do I record", rj["nodes"][0]["title"])

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

    def test_captcha(self):
        resp = self.client.get(
            "/api/captcha/img",
        )
        self.assertEqual(200, resp.status_code)
        self.assertEqual("image/png", resp.headers["content-type"])
        self.assertGreater(len(resp.headers["x-captcha-token"]), 0)

        code_str = jwt_decode(resp.headers["x-captcha-token"])["code"]
        resp = self.client.post(
            "/api/captcha/img",
            json={
                "requestId": "xxx",
                "token": resp.headers["x-captcha-token"],
                "codeStr": code_str,
            }
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
