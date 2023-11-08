import datetime
import io
import os
import time
import unittest
from typing import Dict
from zipfile import ZipFile

from PIL import Image
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
        resp = self.client.put(
            "/api/search/recent",
            json={
                "requestId": "xxx",
                "query": "aaa",
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
        self.assertEqual(["aaa"], rj["queries"])

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

    def test_batch(self):
        base_count = 2
        for i in range(10):
            resp = self.client.put("/api/node", json={
                "requestId": "xxx",
                "md": f"node{i}\ntext",
                "type": const.NodeType.MARKDOWN.value,
            }, headers={"token": self.token})
            rj = resp.json()
            self.assertEqual(0, rj["code"])
        resp = self.client.post(
            "/api/search/node",
            json={
                "query": "",
                "requestId": "xxx",
                "sortKey": "createdAt",
                "sortOrder": -1, "page": 0, "pageSize": 5},
            headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual(5, len(rj["data"]["nodes"]))
        self.assertEqual(10 + base_count, rj["data"]["total"])

        resp = self.client.put(
            "/api/trash/batch",
            json={
                "requestId": "xxx",
                "nids": [n["id"] for n in rj["data"]["nodes"][:3]],
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
        self.assertEqual(3, len(rj["data"]["nodes"]))
        self.assertEqual(3, rj["data"]["total"])

        resp = self.client.post(
            "/api/trashRestore/batch",
            json={
                "requestId": "xxx",
                "nids": [n["id"] for n in rj["data"]["nodes"][:2]],
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
        self.assertEqual(1, rj["data"]["total"])

        resp = self.client.post(
            "/api/trashDelete/batch",
            json={
                "requestId": "xxx",
                "nids": [n["id"] for n in rj["data"]["nodes"]],
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
        self.assertEqual(0, len(rj["data"]["nodes"]))
        self.assertEqual(0, rj["data"]["total"])

    def test_update_obsidian(self):
        image = Image.new('RGB', (4, 4))
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        orig_data: Dict[str, bytes] = {
            "test1.md": "111\n[[qa]] ![img/p.png](img/p.png)".encode("utf-8"),
            "test2.md": "111\n\nasdq[[test]] ![[Pasted image 20230810112909.png]]".encode("utf-8"),
            "test3.md": "111\n\n![[Pasted image 20230810112931.png]]".encode("utf-8"),
            "20230810112909.png": img_byte_arr.getvalue(),
            os.path.join("img", "p.png"): img_byte_arr.getvalue(),
            os.path.join("img", "20230810112931.png"): img_byte_arr.getvalue(),
        }
        # write dummy zip file
        zip_bytes = ZipFile("test.zip", "w")
        for k, v in orig_data.items():
            zip_bytes.writestr(k, v)
        zip_bytes.close()
        f = open("test.zip", "rb")

        resp = self.client.post(
            "/api/files/obsidian",
            files=[
                ("files", f),
            ],
            headers={
                "token": self.token
            },
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"], msg=rj)

        for _ in range(8):
            time.sleep(0.1)
            resp = self.client.get(
                "/api/files/uploadProcess",
                params={"rid": "xxx"},
                headers={"token": self.token}
            )
            rj = resp.json()
            self.assertEqual("obsidian", rj["type"], msg=rj)
            self.assertEqual([], rj["problemFiles"], msg=rj)
            if rj["process"] == 100:
                break
        self.assertFalse(rj["running"], msg=rj)

        resp = self.client.post(
            "/api/search/node",
            json={
                "query": "",
                "requestId": "xxx",
                "sortKey": "createdAt",
                "sortOrder": -1, "page": 0, "pageSize": 5},
            headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual(5, len(rj["data"]["nodes"]))
        self.assertEqual(5, rj["data"]["total"])

        f.close()
        os.remove("test.zip")

    def test_upload_text(self):
        os.makedirs("temp", exist_ok=True)
        f1 = open("temp/test1.txt", "wb+")
        f1.write("dasd".encode("utf-8"))
        f2 = open("temp/test2.txt", "wb+")
        f2.write("asdq".encode("utf-8"))

        resp = self.client.post(
            "/api/files/text",
            files=[
                ("files", f1),
                ("files", f2),
            ],
            headers={
                "token": self.token
            },
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])

        for _ in range(8):
            time.sleep(0.1)
            resp = self.client.get(
                "/api/files/uploadProcess",
                params={"rid": "xxx"},
                headers={"token": self.token}
            )
            rj = resp.json()
            self.assertEqual("text", rj["type"], msg=rj)
            self.assertEqual([], rj["problemFiles"], msg=rj)
            if rj["process"] == 100:
                break
        self.assertFalse(rj["running"], msg=rj)

        resp = self.client.post(
            "/api/search/node",
            json={
                "query": "",
                "requestId": "xxx",
                "sortKey": "createdAt",
                "sortOrder": -1, "page": 0, "pageSize": 5},
            headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual(4, len(rj["data"]["nodes"]))

        f1.close()
        f2.close()
        os.remove("temp/test1.txt")
        os.remove("temp/test2.txt")
        os.rmdir("temp")

    def test_upload_image(self):
        os.makedirs("temp", exist_ok=True)
        image = Image.new('RGB', (4, 4))
        image.save("temp/test.png", format='PNG')
        f1 = open("temp/test.png", "rb")
        resp = self.client.post(
            "/api/files/imageUploadVditor",
            files={"file[]": f1},
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual({
            'errFiles': [],
            'succMap': {
                'test.png': 'http://127.0.0.1:8000/i/3acca26d4f9d111694d7dbda2d1e6a40.png'
            }}, rj["data"])
        f1.close()
        os.remove("temp/test.png")
        os.rmdir("temp")
