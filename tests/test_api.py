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

from retk import const, config, PluginAPICallReturn
from retk.application import app
from retk.core import account
from retk.models.client import client
from retk.models.tps import convert_user_dict_to_authed_user
from retk.plugins.register import register_official_plugins, unregister_official_plugins
from retk.utils import jwt_decode
from . import utils


class PublicApiTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await client.init()
        self.client = TestClient(app)

    async def asyncTearDown(self) -> None:
        await client.drop()

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    def test_home(self):
        resp = self.client.get("/")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("text/html; charset=utf-8", resp.headers["content-type"])
        self.assertEqual(Response, type(resp))

    def test_register(self):
        token, _ = account.app_captcha.generate()
        data = jwt_decode(token)
        resp = self.client.post(
            "/api/account",
            json={
                "email": "a@c.com",
                "password": "a",
                "captchaToken": token,
                "captchaCode": data["code"],
                "language": const.Language.EN.value,
                "requestId": "xxx"
            },
            headers={"RequestId": "xxx"}
        )
        self.assertEqual(403, resp.status_code)
        rj = resp.json()
        self.assertEqual(const.Code.ONE_USER_MODE.value, rj["detail"]["code"])
        self.assertEqual("xxx", rj["detail"]["requestId"])

    @patch(
        "retk.core.account.email.EmailServer._send"
    )
    def test_email_verification(self, mock_send):
        mock_send.return_value = const.Code.OK
        token, _ = account.app_captcha.generate()
        data = jwt_decode(token)

        resp = self.client.put(
            "/api/account/email/send-code",
            json={
                "email": "a@c.com",
                "userExistOk": True,
                "captchaToken": token,
                "captchaCode": data["code"],
                "language": "zh",
            },
            headers={"RequestId": "xxx"}
        )
        self.assertEqual(200, resp.status_code)
        rj = resp.json()
        self.assertNotEqual("", rj["accessToken"])
        self.assertEqual("xxx", rj["requestId"])


class TokenApiTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await client.init()
        self.client = TestClient(app)
        resp = self.client.put(
            "/api/account/login",
            json={
                "email": const.DEFAULT_USER["email"],
                "password": "",
            })
        self.assertEqual(200, resp.status_code)
        rj = resp.json()
        self.assertEqual(818, len(rj["accessToken"]))
        self.assertTrue(rj["accessToken"].startswith("Bearer "))
        self.refresh_token = rj["refreshToken"]
        self.default_headers = {
            "Authorization": rj["accessToken"],
            "RequestId": "xxx",
        }

    async def asyncTearDown(self) -> None:
        await client.drop()
        shutil.rmtree(Path(__file__).parent / "tmp" / ".data" / "files", ignore_errors=True)
        shutil.rmtree(Path(__file__).parent / "tmp" / ".data" / "md", ignore_errors=True)

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    def error_check(self, resp: Response, status_code: int, code: const.Code, rid="xxx", language="en"):
        self.assertEqual(status_code, resp.status_code)
        rj = resp.json()
        self.assertIn("detail", rj, msg=rj)
        detail = rj["detail"]
        self.assertEqual(code.value, detail["code"], msg=detail)
        self.assertEqual(rid, detail["requestId"], msg=detail)
        self.assertEqual(const.get_msg_by_code(code, language=language), detail["msg"], msg=detail)

    def check_ok_response(self, resp: Response, status_code: int = 200, rid="xxx") -> dict:
        self.assertEqual(status_code, resp.status_code)
        rj = resp.json()
        self.assertEqual(rid, rj["requestId"])
        return rj

    async def test_access_token_expire(self):
        aed = config.get_settings().ACCESS_TOKEN_EXPIRE_DELTA
        red = config.get_settings().REFRESH_TOKEN_EXPIRE_DELTA

        config.get_settings().ACCESS_TOKEN_EXPIRE_DELTA = datetime.timedelta(microseconds=1)
        config.get_settings().REFRESH_TOKEN_EXPIRE_DELTA = datetime.timedelta(microseconds=2)
        resp = self.client.put(
            "/api/account/login",
            json={
                "email": const.DEFAULT_USER["email"],
                "password": "",
            })
        rj = resp.json()
        access_token = rj["accessToken"]
        refresh_token = rj["refreshToken"]
        time.sleep(0.001)

        resp = self.client.get(
            "/api/users",
            headers={
                "Authorization": access_token,
                "RequestId": "xxx"
            }
        )
        self.error_check(resp, 401, const.Code.EXPIRED_AUTH)

        resp = self.client.get(
            "/api/account/access-token",
            headers={
                "Authorization": refresh_token,
                "RequestId": "xxx"
            }
        )
        self.error_check(resp, 401, const.Code.EXPIRED_AUTH)

        config.get_settings().REFRESH_TOKEN_EXPIRE_DELTA = red

        resp = self.client.put(
            "/api/account/login",
            json={
                "email": const.DEFAULT_USER["email"],
                "password": "",
            })
        rj = resp.json()
        access_token = rj["accessToken"]
        refresh_token = rj["refreshToken"]
        time.sleep(0.001)

        resp = self.client.get(
            "/api/users",
            headers={
                "Authorization": access_token,
                "RequestId": "xxx"
            }
        )
        self.error_check(resp, 401, const.Code.EXPIRED_AUTH)

        config.get_settings().ACCESS_TOKEN_EXPIRE_DELTA = aed
        resp = self.client.get(
            "/api/account/access-token",
            headers={
                "Authorization": refresh_token,
                "RequestId": "xxx"
            }
        )
        rj = self.check_ok_response(resp, 200)
        self.assertNotEqual(access_token, rj["accessToken"])
        self.assertTrue(rj["accessToken"].startswith("Bearer "))
        self.assertEqual("", rj["refreshToken"])

        resp = self.client.get(
            "/api/users",
            headers={
                "Authorization": rj["accessToken"],
                "RequestId": "xxx"
            }
        )
        self.check_ok_response(resp, 200)

    async def test_get_new_access_token(self):
        time.sleep(0.001)
        resp = self.client.get(
            "/api/account/access-token",
            headers={
                "Authorization": self.refresh_token,
                "RequestId": "xxx",
            }
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(818, len(rj["accessToken"]))
        self.assertTrue(self.default_headers["Authorization"] != rj["accessToken"])
        self.assertTrue(rj["accessToken"].startswith("Bearer "))
        self.assertEqual("", rj["refreshToken"])

    async def test_add_user_update_password(self):
        config.get_settings().ONE_USER = False
        config.get_settings().DB_SALT = "test"
        token, code = account.app_captcha.generate()
        data = jwt_decode(token)
        code = data["code"].replace(config.get_settings().CAPTCHA_SALT, "")

        email = "a@b.c"
        resp = self.client.get(
            "/api/users",
            headers={
                "Authorization": "xxxx",
                "RequestId": "xxx"
            })
        self.assertEqual(401, resp.status_code)
        self.error_check(resp, 401, const.Code.INVALID_AUTH)

        lang = "zh"
        resp = self.client.post(
            "/api/account",
            json={
                "email": email,
                "password": "abc111",
                "captchaToken": token,
                "captchaCode": code,
                "language": lang,
            },
            headers={"RequestId": "xxx"}
        )
        rj = self.check_ok_response(resp, 201)
        u_token = rj["accessToken"]
        self.assertNotEqual("", u_token)

        resp = self.client.get(
            "/api/users",
            headers={
                "Authorization": rj["accessToken"],
                "RequestId": "xxx"
            })
        rj = self.check_ok_response(resp, 200)
        self.assertEqual("a**@b.c", rj["user"]["email"])
        self.assertEqual("zh", rj["user"]["settings"]["language"])

        resp = self.client.put(
            "/api/users/password",
            json={
                "oldPassword": "xxx111",
                "newPassword": "abc222",
            },
            headers={
                "Authorization": u_token,
                "RequestId": "xxx"
            }
        )
        self.error_check(resp, 400, const.Code.OLD_PASSWORD_ERROR, language=lang)

        resp = self.client.put(
            "/api/users/password", json={
                "email": email,
                "oldPassword": "abc111",
                "newPassword": "abc222",
            },
            headers={
                "Authorization": u_token,
                "RequestId": "xxx",
            }
        )
        _ = self.check_ok_response(resp, 200)
        u = await client.coll.users.find_one({"email": email})
        au = convert_user_dict_to_authed_user(u)
        self.assertTrue(await account.manager.is_right_password(
            email=au.email,
            hashed=au.hashed,
            password="abc222"
        ))

        uid = (await client.coll.users.find_one({"email": email}))["id"]
        await client.coll.users.delete_one({"id": uid})
        await client.coll.nodes.delete_many({"uid": uid})
        config.get_settings().ONE_USER = True

    def test_get_user(self):
        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual("rethink", rj["user"]["nickname"])
        self.assertGreater(
            datetime.datetime.strptime(
                rj["user"]["createdAt"], "%Y-%m-%dT%H:%M:%SZ"
            ).timestamp(),
            0., msg=rj["user"]["createdAt"])

    def test_update_user(self):
        resp = self.client.patch(
            "/api/users",
            json={
                "nickname": "new nickname",
                "avatar": "http://new.avatar/aa.png",
                "lastState": {
                    "nodeDisplayMethod": const.NodeDisplayMethod.LIST.value,
                }
            },
            headers=self.default_headers
        )
        _ = self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/users",
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual("new nickname", rj["user"]["nickname"])
        self.assertEqual("http://new.avatar/aa.png", rj["user"]["avatar"])
        self.assertEqual(const.NodeDisplayMethod.LIST.value, rj["user"]["lastState"]["nodeDisplayMethod"])

        resp = self.client.patch(
            "/api/users",
            json={
                "settings": {
                    "language": const.Language.ZH.value,
                    "theme": "dark",
                    "editorMode": "ir",
                    "editorFontSize": 20,
                    "editorCodeTheme": "dracula",
                }
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual("zh", rj["user"]["settings"]["language"])
        self.assertEqual("ir", rj["user"]["settings"]["editorMode"])
        self.assertEqual("dark", rj["user"]["settings"]["theme"])
        self.assertEqual(20, rj["user"]["settings"]["editorFontSize"])
        self.assertEqual("dracula", rj["user"]["settings"]["editorCodeTheme"])

    def test_recent_search(self):
        resp = self.client.get(
            "/api/nodes",
            params={
                "q": "aaa",
                "p": 0,
                "limit": 5
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/recent/searched",
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(["aaa"], rj["queries"])

    def test_node(self):
        resp = self.client.get(
            "/api/nodes",
            params={
                "q": "",
                "sort": "createdAt",
                "ord": "desc",
                "p": 0,
                "limit": 5
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertGreater(len(rj["data"]["nodes"]), 0)

        self.client.get(
            "/api/nodes",
            params={
                "q": "",
                "sort": "createdAt",
                "ord": "desc",
                "p": 0,
                "limit": 5
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)

        resp = self.client.post(
            "/api/nodes",
            json={
                "md": "node1\ntext",
                "type": const.NodeType.MARKDOWN.value,
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 201)
        node = rj["node"]

        resp = self.client.get(
            f'/api/nodes/{node["id"]}',
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        n = rj["node"]
        self.assertEqual("node1", n["title"], msg=rj)
        self.assertEqual("node1\ntext", n["md"])
        self.assertEqual(const.NodeType.MARKDOWN.value, n["type"])

        resp = self.client.put(
            f'/api/nodes/{node["id"]}/md',
            json={
                "md": "node2\ntext",
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)

        resp = self.client.get(
            f'/api/nodes/{node["id"]}',
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        n = rj["node"]
        self.assertEqual("xxx", rj["requestId"])
        self.assertEqual("node2", n["title"])
        self.assertEqual("node2\ntext", n["md"])
        self.assertEqual(const.NodeType.MARKDOWN.value, n["type"])

        resp = self.client.put(
            f'/api/trash/{node["id"]}',
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/trash",
            params={"p": 0, "limit": 10},
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(1, len(rj["data"]["nodes"]))

        resp = self.client.put(
            f'/api/trash/{node["id"]}/restore',
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)

        resp = self.client.get(
            f'/api/nodes/{node["id"]}/at',
            params={
                "q": "How",
                "p": 0,
                "limit": 10,
            },
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(2, len(rj["data"]["nodes"]))
        self.assertEqual("Welcome to Rethink", rj["data"]["nodes"][0]["title"])

        resp = self.client.get(
            f'/api/nodes/{node["id"]}/recommend',
            params={
                "content": "I do need a Knowledge Management System. This is a good one to try.",
            },
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(1, len(rj["data"]["nodes"]))
        self.assertEqual(1, rj["data"]["total"])
        self.assertEqual("Welcome to Rethink", rj["data"]["nodes"][0]["title"])

        self.client.put(
            f'/api/trash/{node["id"]}',
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        resp = self.client.delete(
            f"/api/trash/{node['id']}",
            headers=self.default_headers
        )
        self.assertEqual(200, resp.status_code)
        rj = resp.json()

        resp = self.client.delete(
            "/api/trash/ssa",
            headers=self.default_headers
        )
        self.error_check(resp, 404, const.Code.NODE_NOT_EXIST)

        resp = self.client.get(
            f'/api/nodes/{node["id"]}',
            headers=self.default_headers
        )
        self.error_check(resp, 404, const.Code.NODE_NOT_EXIST)

        resp = self.client.get(
            "/api/nodes/core",
            params={
                "p": 0,
                "limit": 10,
            },
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(2, rj["data"]["total"])
        self.assertEqual(2, len(rj["data"]["nodes"]))

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
            resp = self.client.post(
                "/api/nodes",
                json={
                    "md": f"node{i}\ntext",
                    "type": const.NodeType.MARKDOWN.value,
                },
                headers=self.default_headers
            )
            self.check_ok_response(resp, 201)

        resp = self.client.get(
            "/api/nodes",
            params={
                "q": "",
                "sort": "createdAt",
                "ord": "desc",
                "p": 0,
                "limit": 5
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(5, len(rj["data"]["nodes"]))
        self.assertEqual(10 + base_count, rj["data"]["total"])

        resp = self.client.put(
            "/api/trash/batch",
            json={
                "nids": [n["id"] for n in rj["data"]["nodes"][:3]],
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/trash",
            params={"p": 0, "limit": 10},
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(3, len(rj["data"]["nodes"]))
        self.assertEqual(3, rj["data"]["total"])

        resp = self.client.put(
            "/api/trash/batch/restore",
            json={
                "nids": [n["id"] for n in rj["data"]["nodes"][:2]],
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/trash",
            params={"p": 0, "limit": 10},
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(1, len(rj["data"]["nodes"]))
        self.assertEqual(1, rj["data"]["total"])

        resp = self.client.put(
            "/api/trash/batch/delete",
            json={
                "nids": [n["id"] for n in rj["data"]["nodes"]],
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        resp = self.client.get(
            "/api/trash",
            params={"p": 0, "limit": 10},
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
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
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 202)

        for _ in range(10):
            time.sleep(0.1)
            resp = self.client.get(
                "/api/files/upload-process",
                headers=self.default_headers
            )
            rj = self.check_ok_response(resp, 200)
            self.assertEqual("obsidian", rj["type"], msg=rj)
            self.assertEqual("done", rj["msg"], msg=rj)
            if rj["process"] == 100:
                break
        self.assertFalse(rj["running"], msg=rj)

        resp = self.client.get(
            "/api/nodes",
            params={
                "q": "",
                "sort": "createdAt",
                "ord": "desc",
                "p": 0,
                "limit": 5,
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
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
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 202)

        for _ in range(10):
            time.sleep(0.1)
            resp = self.client.get(
                "/api/files/upload-process",
                headers=self.default_headers
            )
            self.assertEqual(200, resp.status_code)
            rj = resp.json()
            self.assertEqual("md", rj["type"], msg=rj)
            self.assertEqual("done", rj["msg"], msg=rj)
            if rj["process"] == 100:
                break
        self.assertFalse(rj["running"], msg=rj)

        resp = self.client.get(
            "/api/nodes",
            params={
                "q": "",
                "sort": "createdAt",
                "ord": "desc",
                "p": 0,
                "limit": 5,
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
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
            "/api/files/vditor",
            files={"file[]": f1},
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual({
            'errFiles': [],
            'succMap': {
                'test.png': "/files/3acca26d4f9d111694d7dbda2d1e6a40.png"
            }}, rj["data"])
        f1.close()
        shutil.rmtree("temp", ignore_errors=True)

    def test_upload_file(self):
        os.makedirs("temp", exist_ok=True)
        f1 = open("temp/test.txt", "wb+")
        f1.write("dasd".encode("utf-8"))
        resp = self.client.post(
            "/api/files/vditor",
            files={"file[]": f1},
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual({
            'errFiles': [],
            'succMap': {
                'test.txt': "/files/196b0f14eba66e10fba74dbf9e99c22f.txt"
            }}, rj["data"])
        f1.close()
        shutil.rmtree("temp", ignore_errors=True)

    def test_upload_invalid_file(self):
        os.makedirs("temp", exist_ok=True)
        f1 = open("temp/test.qw", "wb+")
        f1.write("dasd".encode("utf-8"))
        resp = self.client.post(
            "/api/files/vditor",
            files={"file[]": f1},
            headers=self.default_headers
        )
        self.assertEqual(200, resp.status_code, msg=resp.json())
        rj = resp.json()
        self.assertEqual(const.Code.INVALID_FILE_TYPE.value, rj["code"])
        self.assertEqual({'errFiles': ['test.qw'], 'succMap': {}}, rj["data"])
        f1.close()
        shutil.rmtree("temp", ignore_errors=True)

    def test_fetch_image(self):
        img = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/" \
              "w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
        resp = self.client.post(
            "/api/files/vditor/images",
            json={"url": img},
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(img, rj["data"]["url"])

        img = "fffew"
        resp = self.client.post(
            "/api/files/vditor/images",
            json={"url": img},
            headers=self.default_headers
        )
        self.error_check(resp, 400, const.Code.FILE_OPEN_ERROR)

    @patch(
        "retk.utils.httpx.AsyncClient.get",
        return_value=Response(200, content="<title>百度一下</title>".encode("utf-8"))
    )
    def test_put_quick_node(self, mocker):
        resp = self.client.post(
            "/api/nodes/quick",
            json={
                "md": "node1\ntext",
                "type": const.NodeType.MARKDOWN.value,
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 201)
        node = rj["node"]
        self.assertEqual("node1", node["title"])
        self.assertEqual("node1\ntext", node["md"])
        self.assertEqual(const.NodeType.MARKDOWN.value, node["type"])

        resp = self.client.post(
            "/api/nodes/quick",
            json={
                "md": "https://baidu.com",
                "type": const.NodeType.MARKDOWN.value,
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 201)
        node = rj["node"]
        self.assertIn("https://baidu.com", node["md"])
        self.assertIn("百度", node["md"])

    def test_system_latest_version(self):
        resp = self.client.get(
            "/api/system/latest-version",
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        for n in rj["remote"]:
            self.assertTrue(isinstance(n, int))
        for n in rj["local"]:
            self.assertTrue(isinstance(n, int))

    @patch("retk.core.node.backup.__remove_md_all_versions_from_cos")
    @patch("retk.core.node.backup.__remove_md_from_cos")
    @patch("retk.core.node.backup.__get_md_from_cos")
    @patch("retk.core.node.backup.__save_md_to_cos")
    def test_md_history(
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
        resp = self.client.post(
            "/api/nodes",
            json={
                "md": "title\ntext",
                "type": const.NodeType.MARKDOWN.value,
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 201)
        n1 = rj["node"]

        time.sleep(0.001)

        resp = self.client.put(
            f"/api/nodes/{n1['id']}/md",
            json={
                "md": "title1\ntext",
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)

        time.sleep(0.001)

        resp = self.client.put(
            f"/api/nodes/{n1['id']}/md",
            json={
                "md": "title2\ntext",
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)

        resp = self.client.get(
            f"/api/nodes/{n1['id']}/history",
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        hist = rj["versions"]
        self.assertEqual(2, len(hist))

        resp = self.client.get(
            f"/api/nodes/{n1['id']}/history/{hist[1]}/md",
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual("title1\ntext", rj["md"])

        config.get_settings().MD_BACKUP_INTERVAL = bi

    @patch("retk.plugins.base.Plugin.handle_api_call")
    def test_plugin(self, mock_handle_api_call):
        def check_one_plugin(ps):
            self.assertGreater(len(ps), 1)
            p = ps[0]
            self.assertIn("id", p)
            self.assertIn("name", p)
            self.assertIn("version", p)
            self.assertIn("description", p)
            self.assertIn("author", p)
            self.assertIn("iconSrc", p)

        config.get_settings().PLUGINS = True
        register_official_plugins()
        resp = self.client.get(
            "/api/plugins",
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        check_one_plugin(rj["plugins"])

        resp = self.client.get(
            "/api/plugins/editor-side",
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        check_one_plugin(rj["plugins"])
        pid = rj["plugins"][0]["id"]

        resp = self.client.get(
            f"/api/plugins/{pid}",
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertNotEqual("", rj["html"])

        resp = self.client.get(
            "/api/nodes",
            params={
                "q": "",
                "sort": "createdAt",
                "ord": "desc",
                "p": 0,
                "limit": 5,
            },
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        nid = rj["data"]["nodes"][0]["id"]

        resp = self.client.get(
            f"/api/plugins/{pid}/editor-side/{nid}",
            headers=self.default_headers
        )
        rj = self.check_ok_response(resp, 200)
        self.assertNotEqual("", rj["html"])

        resp = self.client.post(
            "/api/plugins/call",
            json={
                "requestId": "xxx",
                "pluginId": "xasdqw",
                "method": "test",
                "data": "test",
            },
            headers=self.default_headers
        )
        rj = resp.json()
        self.assertEqual(False, rj["success"])

        mock_handle_api_call.return_value = PluginAPICallReturn(
            success=True,
            message="",
            data="test"
        )
        resp = self.client.post(
            "/api/plugins/call",
            json={
                "pluginId": pid,
                "method": "method",
                "data": "test",
            },
            headers=self.default_headers
        )
        rj = resp.json()
        self.assertEqual("method", rj["method"])
        self.assertEqual("test", rj["data"])

        unregister_official_plugins()
        config.get_settings().PLUGINS = False

    async def test_admin(self):
        resp = self.client.put(
            "/api/admin/users/disable",
            json={
                "uid": "xxx",
            },
            headers=self.default_headers
        )
        self.error_check(resp, 403, const.Code.NOT_PERMITTED)

        u = await client.coll.users.find_one({"email": const.DEFAULT_USER["email"]})
        admin_uid = u["id"]
        doc = await client.coll.users.update_one(
            {"id": admin_uid},
            {"$set": {"type": const.USER_TYPE.ADMIN.id}}
        )
        self.assertEqual(1, doc.modified_count)

        resp = self.client.put(
            "/api/admin/users/disable",
            json={
                "uid": "xxx",
            },
            headers=self.default_headers
        )
        self.check_ok_response(resp, 200)

        config.get_settings().ONE_USER = False
        config.get_settings().DB_SALT = "test"
        token, code = account.app_captcha.generate()
        data = jwt_decode(token)
        code = data["code"].replace(config.get_settings().CAPTCHA_SALT, "")
        lang = "zh"
        email = "a@b.cd"
        resp = self.client.post(
            "/api/account",
            json={
                "email": email,
                "password": "abc111",
                "captchaToken": token,
                "captchaCode": code,
                "language": lang,
            },
            headers={"RequestId": "xxx"}
        )
        rj = self.check_ok_response(resp, 201)
        u_token = rj["accessToken"]
        uid = (await client.coll.users.find_one({"email": email}))["id"]

        resp = self.client.get(
            "/api/users",
            headers={
                "Authorization": u_token,
                "RequestId": "xxx"
            }
        )
        self.check_ok_response(resp, 200)

        resp = self.client.put(
            "/api/admin/users/disable",
            json={
                "uid": uid,
            },
            headers=self.default_headers
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/users",
            headers={
                "Authorization": u_token,
                "RequestId": "xxx"
            }
        )
        self.error_check(resp, 403, const.Code.USER_DISABLED)

        resp = self.client.put(
            "/api/admin/users/enable/email",
            json={
                "email": email,
            },
            headers=self.default_headers
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/users",
            headers={
                "Authorization": u_token,
                "RequestId": "xxx"
            }
        )
        self.check_ok_response(resp, 200)

        resp = self.client.put(
            "/api/admin/users/delete",
            json={
                "uid": uid,
            },
            headers=self.default_headers
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/users",
            headers={
                "Authorization": u_token,
                "RequestId": "xxx"
            }
        )
        self.error_check(resp, 403, const.Code.USER_DISABLED)

        doc = await client.coll.users.update_one(
            {"id": admin_uid},
            {"$set": {"type": const.USER_TYPE.NORMAL.id}}
        )
        self.assertEqual(1, doc.modified_count)
        config.get_settings().ONE_USER = True
