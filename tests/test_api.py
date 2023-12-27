import datetime
import io
import os
import shutil
import time
import unittest
from pathlib import Path
from typing import Dict
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image
from fastapi.testclient import TestClient
from httpx import Response

from rethink import const
from rethink.application import app
from rethink.models import database
from rethink.models.utils import jwt_decode
from rethink.models.verify import verification
from . import utils


class PublicApiTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await database.init()
        self.client = TestClient(app)

    async def asyncTearDown(self) -> None:
        await database.drop_all()

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    def test_home(self):
        resp = self.client.get("/")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("text/html; charset=utf-8", resp.headers["content-type"])
        self.assertEqual(Response, type(resp))

    def test_register(self):
        token, _ = verification.random_captcha()
        data = jwt_decode(token)
        resp = self.client.put("/api/user", json={
            "email": "a@c.com",
            "password": "a",
            "captchaToken": token,
            "captchaCode": data["code"],
            "language": const.Language.EN.value,
            "requestId": "xxx"
        })
        rj = resp.json()
        self.assertEqual(const.Code.ONE_USER_MODE.value, rj["code"])
        self.assertEqual(len(rj["token"]), 0)
        self.assertEqual("xxx", rj["requestId"])


class TokenApiTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await database.init()
        self.client = TestClient(app)
        resp = self.client.post("/api/login", json={
            "email": const.DEFAULT_USER["email"],
            "password": "",
        })
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.token = rj["token"]
        self.assertEqual(811, len(self.token))

    async def asyncTearDown(self) -> None:
        await database.drop_all()
        shutil.rmtree(Path(__file__).parent / "tmp" / ".data" / "files", ignore_errors=True)
        shutil.rmtree(Path(__file__).parent / "tmp" / ".data" / "md", ignore_errors=True)

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    def test_get_user(self):
        resp = self.client.get(
            "/api/user",
            headers={"token": self.token, "rid": "xxx"})
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

        resp = self.client.get(
            "/api/user",
            headers={"token": self.token, "rid": "xxx"}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("new nickname", rj["user"]["nickname"])
        self.assertEqual("http://new.avatar/aa.png", rj["user"]["avatar"])
        self.assertEqual(const.NodeDisplayMethod.LIST.value, rj["user"]["lastState"]["nodeDisplayMethod"])
        self.assertEqual("xxx", rj["requestId"])

    def test_recent_search(self):
        resp = self.client.post(
            "/api/search/node",
            json={
                "requestId": "xxx",
                "query": "aaa",
                "page": 0, "pageSize": 5
            }, headers={"token": self.token})
        rj = resp.json()
        self.assertEqual(0, rj["code"], msg=rj)

        resp = self.client.get(
            "/api/search/recent",
            headers={"token": self.token, "rid": "xxx"}
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
            params={"nid": node["id"]},
            headers={"token": self.token, "rid": "xxx"}
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
            params={"nid": node["id"]},
            headers={"token": self.token, "rid": "xxx"}
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
            params={"p": 0, "ps": 10},
            headers={"token": self.token, "rid": "xxx"}
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
                "query": "How",
                "page": 0,
                "pageSize": 10,
            },
            headers={"token": self.token},
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
        self.assertEqual(2, len(rj["data"]["nodes"]))
        self.assertEqual("Welcome to Rethink", rj["data"]["nodes"][0]["title"])

        resp = self.client.post(
            "/api/search/recommend",
            json={
                "requestId": "xxx",
                "content": "I do need a Knowledge Management System. This is a good one to try.",
                "nidExclude": [],
            },
            headers={"token": self.token},
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
        self.assertEqual(1, len(rj["nodes"]))
        self.assertEqual("Welcome to Rethink", rj["nodes"][0]["title"])

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
            params={"nid": node["id"]},
            headers={"token": self.token, "rid": "xxx"}
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
            params={"p": 0, "ps": 10},
            headers={"token": self.token, "rid": "xxx"}
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
            params={"p": 0, "ps": 10},
            headers={"token": self.token, "rid": "xxx"}
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
            params={"p": 0, "ps": 10},
            headers={"token": self.token, "rid": "xxx"}
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

        for _ in range(10):
            time.sleep(0.1)
            resp = self.client.get(
                "/api/files/uploadProcess",
                headers={"token": self.token, "rid": "xxx"}
            )
            rj = resp.json()
            self.assertEqual("obsidian", rj["type"], msg=rj)
            self.assertEqual("done", rj["msg"], msg=rj)
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

        for _ in range(10):
            time.sleep(0.1)
            resp = self.client.get(
                "/api/files/uploadProcess",
                headers={"token": self.token, "rid": "xxx"}
            )
            rj = resp.json()
            self.assertEqual("md", rj["type"], msg=rj)
            self.assertEqual("done", rj["msg"], msg=rj)
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
        shutil.rmtree("temp", ignore_errors=True)

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
                'test.png': "/files/3acca26d4f9d111694d7dbda2d1e6a40.png"
            }}, rj["data"])
        f1.close()
        shutil.rmtree("temp", ignore_errors=True)

    def test_fetch_image(self):
        img = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/" \
              "w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
        resp = self.client.post(
            "/api/files/imageFetchVditor",
            json={"url": img},
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual(img, rj["data"]["url"])

    @patch(
        "rethink.models.utils.httpx.AsyncClient.get",
        return_value=Response(200, content="<title>百度一下</title>".encode("utf-8"))
    )
    def test_put_quick_node(self, mocker):
        resp = self.client.put(
            "/api/node/quick",
            json={
                "requestId": "xxx",
                "md": "node1\ntext",
                "type": const.NodeType.MARKDOWN.value,
            },
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
        node = rj["node"]
        self.assertEqual("node1", node["title"])
        self.assertEqual("node1\ntext", node["md"])
        self.assertEqual(const.NodeType.MARKDOWN.value, node["type"])

        resp = self.client.put(
            "/api/node/quick",
            json={
                "requestId": "xxx",
                "md": "https://baidu.com",
                "type": const.NodeType.MARKDOWN.value,
            },
            headers={"token": self.token}
        )
        rj = resp.json()
        self.assertEqual(0, rj["code"])
        self.assertEqual("xxx", rj["requestId"])
        node = rj["node"]
        self.assertIn("https://baidu.com", node["md"])
        self.assertIn("百度", node["md"])
