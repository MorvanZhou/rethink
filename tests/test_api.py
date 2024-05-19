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
from bson.tz_util import utc
from fastapi.testclient import TestClient
from httpx import Response

from retk import const, config, PluginAPICallReturn
from retk.application import app
from retk.core import account, scheduler
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
        resp = self.client.put(
            "/api/account/auto-login",
            headers={"RequestId": "xxx"},
        )
        self.assertEqual(200, resp.status_code)
        rj = resp.json()
        self.assertEqual("xxx", rj["requestId"])
        self.assertIsNone(rj["user"])

        token, _ = account.app_captcha.generate()
        data = jwt_decode(token)
        resp = self.client.post(
            "/api/account",
            json={
                "email": "a@c.com",
                "password": "a",
                "verificationToken": token,
                "verification": data["code"],
                "language": const.LanguageEnum.EN.value,
                "requestId": "xxx"
            },
            headers={"RequestId": "xxx"}
        )
        self.assertEqual(403, resp.status_code)
        rj = resp.json()
        self.assertEqual(const.CodeEnum.ONE_USER_MODE.value, rj["detail"]["code"])
        self.assertEqual("xxx", rj["detail"]["requestId"])

    @patch(
        "retk.core.account.email.EmailServer._send"
    )
    def test_email_verification(self, mock_send):
        mock_send.return_value = const.CodeEnum.OK
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
        self.assertNotEqual("", rj["token"])
        self.assertEqual("xxx", rj["requestId"])


class TokenApiTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        scheduler.start()
        await client.init()
        self.client = TestClient(app)
        resp = self.client.put(
            "/api/account/login",
            json={
                "email": const.DEFAULT_USER["email"],
                "password": "",
            })
        self.assertEqual(200, resp.status_code, msg=resp.json())
        self.access_token = resp.cookies.get(const.settings.COOKIE_ACCESS_TOKEN)
        self.refresh_token_id = resp.cookies.get(const.settings.COOKIE_REFRESH_TOKEN_ID)
        self.refresh_token = resp.cookies.get(const.settings.COOKIE_REFRESH_TOKEN)

        self.assertEqual(842, len(self.access_token))
        self.assertTrue(self.access_token.startswith("\"Bearer "), msg=self.access_token)
        self.assertTrue(self.refresh_token.startswith("\"Bearer "), msg=self.access_token)
        self.default_headers = {
            "RequestId": "xxx",
        }

        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        rj = resp.json()
        self.assertEqual(200, resp.status_code, msg=rj)
        self.assertNotIn("detail", rj)

    async def asyncTearDown(self) -> None:
        config.get_settings().ONE_USER = True
        self.client.cookies.clear()
        scheduler.stop()
        await client.drop()
        self.client.close()
        shutil.rmtree(Path(__file__).parent / "tmp" / const.settings.DOT_DATA / "files", ignore_errors=True)
        shutil.rmtree(Path(__file__).parent / "tmp" / const.settings.DOT_DATA / "md", ignore_errors=True)

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    def error_check(self, resp: Response, status_code: int, code: const.CodeEnum, rid="xxx", language="en"):
        self.assertEqual(status_code, resp.status_code)
        rj = resp.json()
        self.assertIn("detail", rj, msg=rj)
        detail = rj["detail"]
        self.assertEqual(code.value, detail["code"], msg=detail)
        self.assertEqual(rid, detail["requestId"], msg=detail)
        self.assertEqual(const.get_msg_by_code(code, language=language), detail["msg"], msg=detail)

    def check_ok_response(self, resp: Response, status_code: int = 200, rid="xxx") -> dict:
        self.assertEqual(status_code, resp.status_code, msg=resp.json())
        rj = resp.json()
        self.assertEqual(rid, rj["requestId"])
        return rj

    def set_access_token(self, token: str):
        try:
            self.client.cookies.delete(const.settings.COOKIE_ACCESS_TOKEN)
        except KeyError:
            pass
        self.client.cookies[const.settings.COOKIE_ACCESS_TOKEN] = token

    async def create_new_temp_user(self, email):
        config.get_settings().ONE_USER = False
        config.get_settings().DB_SALT = "test"
        token, code = account.app_captcha.generate()
        data = jwt_decode(token)
        code = data["code"].replace(config.get_settings().CAPTCHA_SALT, "")
        lang = "zh"

        resp = self.client.post(
            "/api/account",
            json={
                "email": email,
                "password": "abc111",
                "verificationToken": token,
                "verification": code,
                "language": lang,
            },
            headers={"RequestId": "xxx"}
        )
        self.check_ok_response(resp, 201)
        return resp

    async def set_default_manager(self):
        u = await client.coll.users.find_one({"email": const.DEFAULT_USER["email"]})
        admin_uid = u["id"]
        doc = await client.coll.users.update_one(
            {"id": admin_uid},
            {"$set": {"type": const.USER_TYPE.ADMIN.id}}
        )
        self.assertEqual(1, doc.modified_count)
        return admin_uid

    async def clear_default_manager(self, admin_uid):
        doc = await client.coll.users.update_one(
            {"id": admin_uid},
            {"$set": {"type": const.USER_TYPE.NORMAL.id}}
        )
        self.assertEqual(1, doc.modified_count)

    async def test_auto_login(self):
        resp = self.client.put(
            "/api/account/auto-login",
            headers={"RequestId": "xxx"},
        )
        self.assertEqual(200, resp.status_code)
        rj = resp.json()
        self.assertEqual("xxx", rj["requestId"])
        self.assertIsNotNone(rj["user"])

        self.client.cookies.delete(const.settings.COOKIE_ACCESS_TOKEN)
        resp = self.client.put(
            "/api/account/auto-login",
            headers={"RequestId": "xxx"},
        )
        self.assertEqual(200, resp.status_code)
        self.assertIsNone(resp.json()["user"])

    async def test_access_refresh_token(self):
        self.client.put(
            "/api/account/login",
            json={
                "email": const.DEFAULT_USER["email"],
                "password": "",
            })

        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        self.assertEqual(200, resp.status_code)

        self.set_access_token(resp.cookies.get(const.settings.COOKIE_REFRESH_TOKEN))
        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        self.error_check(resp, 200, const.CodeEnum.EXPIRED_OR_NO_ACCESS_TOKEN)

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
                "language": "zh",
            })
        self.assertEqual(200, resp.status_code)
        time.sleep(0.001)

        resp = self.client.get(
            "/api/users",
            headers={
                "RequestId": "xxx"
            },
        )
        self.assertEqual(200, resp.status_code)
        rj = resp.json()
        detail = rj["detail"]
        self.assertEqual(const.CodeEnum.EXPIRED_OR_NO_ACCESS_TOKEN.value, detail["code"], msg=detail)
        self.assertEqual("xxx", detail["requestId"], msg=detail)

        resp = self.client.get(
            "/api/account/access-token",
            headers=self.default_headers,
        )
        self.error_check(resp, 401, const.CodeEnum.EXPIRED_AUTH)

        config.get_settings().REFRESH_TOKEN_EXPIRE_DELTA = red

        self.client.put(
            "/api/account/login",
            json={
                "email": const.DEFAULT_USER["email"],
                "password": "",
            })

        time.sleep(0.001)

        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        self.assertEqual(200, resp.status_code)
        rj = resp.json()
        self.assertEqual(const.CodeEnum.EXPIRED_OR_NO_ACCESS_TOKEN.value, rj["detail"]["code"], msg=rj)

        config.get_settings().ACCESS_TOKEN_EXPIRE_DELTA = aed
        old_access_token = resp.cookies.get(const.settings.COOKIE_ACCESS_TOKEN)
        resp = self.client.get(
            "/api/account/access-token",
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)
        at = resp.cookies.get(const.settings.COOKIE_ACCESS_TOKEN)
        self.assertNotEqual(old_access_token, at)
        self.assertTrue(at.startswith("\"Bearer "))

        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)
        rj = resp.json()
        self.assertEqual("rethink", rj["user"]["nickname"])

    async def test_add_user_update_password(self):
        config.get_settings().ONE_USER = False
        config.get_settings().DB_SALT = "test"
        token, code = account.app_captcha.generate()
        data = jwt_decode(token)
        code = data["code"].replace(config.get_settings().CAPTCHA_SALT, "")

        email = "a@b.c"
        del self.client.cookies[const.settings.COOKIE_ACCESS_TOKEN]
        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        self.error_check(resp, 200, const.CodeEnum.EXPIRED_OR_NO_ACCESS_TOKEN)

        lang = "zh"
        resp = self.client.post(
            "/api/account",
            json={
                "email": email,
                "password": "abc111",
                "verificationToken": token,
                "verification": code,
                "language": lang,
            },
            headers=self.default_headers
        )
        _ = self.check_ok_response(resp, 201)
        u_token = resp.cookies.get(const.settings.COOKIE_ACCESS_TOKEN)
        self.assertNotEqual("", u_token)

        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual("a**@b.c", rj["user"]["email"])
        self.assertEqual("zh", rj["user"]["settings"]["language"])

        resp = self.client.put(
            "/api/users/password",
            json={
                "oldPassword": "xxx111",
                "newPassword": "abc222",
            },
            headers=self.default_headers,
        )
        self.error_check(resp, 400, const.CodeEnum.OLD_PASSWORD_ERROR, language=lang)

        resp = self.client.put(
            "/api/users/password", json={
                "email": email,
                "oldPassword": "abc111",
                "newPassword": "abc222",
            },
            headers=self.default_headers,
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
                    "nodeDisplayMethod": const.NodeDisplayMethodEnum.LIST.value,
                }
            },
            headers=self.default_headers,
        )
        _ = self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual("new nickname", rj["user"]["nickname"])
        self.assertEqual("http://new.avatar/aa.png", rj["user"]["avatar"])
        self.assertEqual(const.NodeDisplayMethodEnum.LIST.value, rj["user"]["lastState"]["nodeDisplayMethod"])

        resp = self.client.patch(
            "/api/users",
            json={
                "settings": {
                    "language": const.LanguageEnum.ZH.value,
                    "theme": "dark",
                    "editorMode": "ir",
                    "editorFontSize": 20,
                    "editorCodeTheme": "dracula",
                }
            },
            headers=self.default_headers,
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
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/recent/searched",
            headers=self.default_headers,
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
            headers=self.default_headers,
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
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.post(
            "/api/nodes",
            json={
                "md": "node1\ntext",
                "type": const.NodeTypeEnum.MARKDOWN.value,
            },
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 201)
        node = rj["node"]

        resp = self.client.get(
            f'/api/nodes/{node["id"]}',
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        n = rj["node"]
        self.assertEqual("node1", n["title"], msg=rj)
        self.assertEqual("node1\ntext", n["md"])
        self.assertEqual(const.NodeTypeEnum.MARKDOWN.value, n["type"])

        resp = self.client.put(
            f'/api/nodes/{node["id"]}/md',
            json={
                "md": "node2\ntext",
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            f'/api/nodes/{node["id"]}',
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        n = rj["node"]
        self.assertEqual("xxx", rj["requestId"])
        self.assertEqual("node2", n["title"])
        self.assertEqual("node2\ntext", n["md"])
        self.assertEqual(const.NodeTypeEnum.MARKDOWN.value, n["type"])

        resp = self.client.put(
            f'/api/trash/{node["id"]}',
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/trash",
            params={"p": 0, "limit": 10},
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(1, len(rj["data"]["nodes"]))

        resp = self.client.put(
            f'/api/trash/{node["id"]}/restore',
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

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
        self.check_ok_response(resp, 200)
        resp = self.client.delete(
            f"/api/trash/{node['id']}",
            headers=self.default_headers,
        )
        self.assertEqual(200, resp.status_code)

        resp = self.client.delete(
            "/api/trash/ssa",
            headers=self.default_headers,
        )
        self.error_check(resp, 404, const.CodeEnum.NODE_NOT_EXIST)

        resp = self.client.get(
            f'/api/nodes/{node["id"]}',
            headers=self.default_headers,
        )
        self.error_check(resp, 404, const.CodeEnum.NODE_NOT_EXIST)

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
                    "type": const.NodeTypeEnum.MARKDOWN.value,
                },
                headers=self.default_headers,
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
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(5, len(rj["data"]["nodes"]))
        self.assertEqual(10 + base_count, rj["data"]["total"])

        resp = self.client.put(
            "/api/trash/batch",
            json={
                "nids": [n["id"] for n in rj["data"]["nodes"][:3]],
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/trash",
            params={"p": 0, "limit": 10},
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(3, len(rj["data"]["nodes"]))
        self.assertEqual(3, rj["data"]["total"])

        resp = self.client.put(
            "/api/trash/batch/restore",
            json={
                "nids": [n["id"] for n in rj["data"]["nodes"][:2]],
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/trash",
            params={"p": 0, "limit": 10},
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(1, len(rj["data"]["nodes"]))
        self.assertEqual(1, rj["data"]["total"])

        resp = self.client.put(
            "/api/trash/batch/delete",
            json={
                "nids": [n["id"] for n in rj["data"]["nodes"]],
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)
        resp = self.client.get(
            "/api/trash",
            params={"p": 0, "limit": 10},
            headers=self.default_headers,
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
                headers=self.default_headers,
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
            headers=self.default_headers,
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
                headers=self.default_headers,
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
            headers=self.default_headers,
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
            headers=self.default_headers,
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
            headers=self.default_headers,
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
            headers=self.default_headers,
        )
        self.assertEqual(200, resp.status_code, msg=resp.json())
        rj = resp.json()
        self.assertEqual(const.CodeEnum.INVALID_FILE_TYPE.value, rj["code"])
        self.assertEqual({'errFiles': ['test.qw'], 'succMap': {}}, rj["data"])
        f1.close()
        shutil.rmtree("temp", ignore_errors=True)

    def test_fetch_image(self):
        img = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/" \
              "w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
        resp = self.client.post(
            "/api/files/vditor/images",
            json={"url": img},
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(img, rj["data"]["url"])

        img = "fffew"
        resp = self.client.post(
            "/api/files/vditor/images",
            json={"url": img},
            headers=self.default_headers,
        )
        self.error_check(resp, 400, const.CodeEnum.FILE_OPEN_ERROR)

    @patch(
        "retk.utils.httpx.AsyncClient.get",
        return_value=Response(200, content="<title>百度一下</title>".encode("utf-8"))
    )
    def test_put_quick_node(self, mocker):
        resp = self.client.post(
            "/api/nodes/quick",
            json={
                "md": "node1\ntext",
                "type": const.NodeTypeEnum.MARKDOWN.value,
            },
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 201)
        node = rj["node"]
        self.assertEqual("node1", node["title"])
        self.assertEqual("node1\ntext", node["md"])
        self.assertEqual(const.NodeTypeEnum.MARKDOWN.value, node["type"])

        resp = self.client.post(
            "/api/nodes/quick",
            json={
                "md": "https://baidu.com",
                "type": const.NodeTypeEnum.MARKDOWN.value,
            },
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 201)
        node = rj["node"]
        self.assertIn("https://baidu.com", node["md"])
        self.assertIn("百度", node["md"])

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
        mock_save_md_to_cos.return_value = const.CodeEnum.OK
        mock_get_md_from_cos.return_value = ("title2\ntext", const.CodeEnum.OK)
        mock_remove_md_from_cos.return_value = const.CodeEnum.OK
        mock_remove_md_all_versions_from_cos.return_value = const.CodeEnum.OK

        bi = config.get_settings().MD_BACKUP_INTERVAL
        config.get_settings().MD_BACKUP_INTERVAL = 0.0001
        resp = self.client.post(
            "/api/nodes",
            json={
                "md": "title\ntext",
                "type": const.NodeTypeEnum.MARKDOWN.value,
            },
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 201)
        n1 = rj["node"]

        time.sleep(0.001)

        resp = self.client.put(
            f"/api/nodes/{n1['id']}/md",
            json={
                "md": "title1\ntext",
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        time.sleep(0.001)

        resp = self.client.put(
            f"/api/nodes/{n1['id']}/md",
            json={
                "md": "title2\ntext",
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            f"/api/nodes/{n1['id']}/history",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        hist = rj["versions"]
        self.assertEqual(2, len(hist))

        resp = self.client.get(
            f"/api/nodes/{n1['id']}/history/{hist[1]}/md",
            headers=self.default_headers,
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
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        check_one_plugin(rj["plugins"])

        resp = self.client.get(
            "/api/plugins/editor-side",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        check_one_plugin(rj["plugins"])
        pid = rj["plugins"][0]["id"]

        resp = self.client.get(
            f"/api/plugins/{pid}",
            headers=self.default_headers,
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
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        nid = rj["data"]["nodes"][0]["id"]

        resp = self.client.get(
            f"/api/plugins/{pid}/editor-side/{nid}",
            headers=self.default_headers,
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
            headers=self.default_headers,
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
            headers=self.default_headers,
        )
        rj = resp.json()
        self.assertEqual("method", rj["method"])
        self.assertEqual("test", rj["data"])

        unregister_official_plugins()
        config.get_settings().PLUGINS = False

    async def test_manager(self):
        manager_token = self.client.cookies.get(const.settings.COOKIE_ACCESS_TOKEN)
        resp = self.client.put(
            "/api/managers/users/disable",
            json={
                "uid": "xxx",
            },
            headers=self.default_headers,
        )
        self.error_check(resp, 403, const.CodeEnum.NOT_PERMITTED)

        admin_uid = await self.set_default_manager()

        resp = self.client.put(
            "/api/managers/users/disable",
            json={
                "uid": "xxx",
            },
            headers=self.default_headers,
        )
        self.error_check(resp, 404, const.CodeEnum.USER_NOT_EXIST)

        email = "a@b.cd"
        resp = await self.create_new_temp_user(email)

        u_token = resp.cookies.get(const.settings.COOKIE_ACCESS_TOKEN)
        uid = (await client.coll.users.find_one({"email": email}))["id"]

        self.set_access_token(manager_token)
        resp = self.client.put(
            "/api/managers/users",
            json={
                "uid": uid,
            },
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(email, rj["user"]["email"])
        self.assertEqual(uid, rj["user"]["id"])
        self.assertIn("source", rj["user"])

        resp = self.client.put(
            "/api/managers/users",
            json={
                "email": email,
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.put(
            "/api/managers/users",
            json={},
            headers=self.default_headers,
        )
        self.error_check(resp, 400, const.CodeEnum.INVALID_PARAMS)

        resp = self.client.put(
            "/api/managers/users/disable",
            json={
                "uid": uid,
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.put(
            "/api/account/login",
            json={
                "email": email,
                "password": "abc111",
            },
            headers=self.default_headers,
        )
        self.error_check(resp, 403, const.CodeEnum.USER_DISABLED)

        self.set_access_token(u_token)
        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        self.error_check(resp, 404, const.CodeEnum.USER_NOT_EXIST)

        self.set_access_token(manager_token)
        resp = self.client.put(
            "/api/managers/users/enable",
            json={
                "email": email,
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        self.set_access_token(u_token)
        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        self.set_access_token(manager_token)
        resp = self.client.put(
            "/api/managers/users/delete",
            json={
                "uid": uid,
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        self.set_access_token(u_token)
        resp = self.client.get(
            "/api/users",
            headers=self.default_headers,
        )
        self.error_check(resp, 404, const.CodeEnum.USER_NOT_EXIST)

        await self.clear_default_manager(admin_uid)

    async def test_statistic_user_behavior(self):
        # login
        self.client.put(
            "/api/account/login",
            json={
                "email": const.DEFAULT_USER["email"],
                "password": "",
            }
        )
        uid = (await client.coll.users.find_one({"email": const.DEFAULT_USER["email"]})).get("id")
        docs = await client.coll.user_behavior.find(
            {"uid": uid}
        ).to_list(None)
        self.assertEqual(const.UserBehaviorTypeEnum.LOGIN.value, docs[-1]["type"])

        # create node
        resp = self.client.post(
            "/api/nodes",
            json={
                "md": "node1\ntext",
                "type": const.NodeTypeEnum.MARKDOWN.value,
            },
            headers=self.default_headers,
        )
        docs = await client.coll.user_behavior.find(
            {"uid": uid}
        ).to_list(None)
        self.assertEqual(const.UserBehaviorTypeEnum.NODE_CREATE.value, docs[-1]["type"])
        self.assertEqual(resp.json()["node"]["id"], docs[-1]["remark"])

        # quick node
        resp = self.client.post(
            "/api/nodes/quick",
            json={
                "md": "node1\ntext",
                "type": const.NodeTypeEnum.MARKDOWN.value,
            },
            headers=self.default_headers,
        )
        docs = await client.coll.user_behavior.find(
            {"uid": uid}
        ).to_list(None)
        self.assertEqual(const.UserBehaviorTypeEnum.NODE_QUICK_CREATE.value, docs[-1]["type"])
        self.assertEqual(resp.json()["node"]["id"], docs[-1]["remark"])

        # trash node
        self.client.put(
            f"/api/trash/{resp.json()['node']['id']}",
            headers=self.default_headers,
        )
        docs = await client.coll.user_behavior.find(
            {"uid": uid}
        ).to_list(None)
        self.assertEqual(const.UserBehaviorTypeEnum.NODE_TRASHED_OPS.value, docs[-1]["type"])

        # restore node
        self.client.put(
            f"/api/trash/{resp.json()['node']['id']}/restore",
            headers=self.default_headers,
        )
        docs = await client.coll.user_behavior.find(
            {"uid": uid}
        ).to_list(None)
        self.assertEqual(const.UserBehaviorTypeEnum.NODE_RESTORED_OPS.value, docs[-1]["type"])

        # delete node
        self.client.put(
            f"/api/trash/{resp.json()['node']['id']}",
            headers=self.default_headers,
        )
        self.client.delete(
            f"/api/trash/{resp.json()['node']['id']}",
            headers=self.default_headers,
        )
        docs = await client.coll.user_behavior.find(
            {"uid": uid}
        ).to_list(None)
        self.assertEqual(const.UserBehaviorTypeEnum.NODE_DELETED_OPS.value, docs[-1]["type"])

        # search
        self.client.get(
            "/api/nodes",
            params={
                "q": "1",
                "sort": "createdAt",
                "ord": "desc",
                "p": 0,
                "limit": 5
            },
            headers=self.default_headers,
        )
        docs = await client.coll.user_behavior.find(
            {"uid": uid}
        ).to_list(None)
        self.assertEqual(const.UserBehaviorTypeEnum.SEARCH_GLOBAL.value, docs[-1]["type"])
        self.assertEqual("1", docs[-1]["remark"])

        # search at
        self.client.get(
            f"/api/nodes/{resp.json()['node']['id']}/at",
            params={
                "q": "node",
                "p": 0,
                "limit": 10,
            },
            headers=self.default_headers,
        )
        docs = await client.coll.user_behavior.find(
            {"uid": uid}
        ).to_list(None)
        self.assertEqual(const.UserBehaviorTypeEnum.SEARCH_AT.value, docs[-1]["type"])
        self.assertEqual("node", docs[-1]["remark"])

        # logout
        resp = self.client.post(
            "/api/statistic/user-behavior",
            json={
                "type": const.UserBehaviorTypeEnum.LOGOUT.value,
                "remark": "logout",
            },
            headers=self.default_headers,
        )
        self.assertEqual(201, resp.status_code)
        docs = await client.coll.user_behavior.find(
            {"uid": uid}
        ).to_list(None)
        self.assertEqual(const.UserBehaviorTypeEnum.LOGOUT.value, docs[-1]["type"])
        self.assertEqual("logout", docs[-1]["remark"])

    async def test_system_notice(self):
        manager_token = self.client.cookies.get(const.settings.COOKIE_ACCESS_TOKEN)

        email = "a@b.cd"
        resp = await self.create_new_temp_user(email)
        u_token = resp.cookies.get(const.settings.COOKIE_ACCESS_TOKEN)
        self.assertEqual(201, resp.status_code)

        admin_uid = await self.set_default_manager()
        pa = datetime.datetime.now(tz=utc)
        resp = self.client.post(
            "/api/managers/notices/system",
            json={
                "title": "title",
                "content": "content",
                "recipientType": const.notice.RecipientTypeEnum.ALL.value,
                "batchTypeIds": [],
                "publishAt": pa.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            headers=self.default_headers,
        )
        self.error_check(resp, 403, const.CodeEnum.NOT_PERMITTED)

        self.set_access_token(manager_token)
        resp = self.client.post(
            "/api/managers/notices/system",
            json={
                "title": "title",
                "content": "content",
                "recipientType": const.notice.RecipientTypeEnum.ALL.value,
                "batchTypeIds": [],
                "publishAt": pa.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 201)

        resp = self.client.get(
            "/api/managers/notices/system",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(1, rj["total"])
        self.assertEqual(1, len(rj["notices"]))
        self.assertEqual("title", rj["notices"][0]["title"])
        self.assertEqual("<p>content</p>", rj["notices"][0]["html"])
        self.assertEqual("content", rj["notices"][0]["snippet"])
        self.assertEqual(pa.strftime("%Y-%m-%dT%H:%M:%SZ"), rj["notices"][0]["publishAt"])
        self.assertFalse(rj["notices"][0]["scheduled"])

        scheduler.run_once_now(
            job_id="deliver_unscheduled_system_notices1",
            func=scheduler.tasks.notice.deliver_unscheduled_system_notices,
        )

        docs = await client.coll.notice_manager_delivery.find(
            {"senderId": admin_uid}
        ).to_list(None)
        self.assertEqual(1, len(docs))
        self.assertEqual(const.notice.RecipientTypeEnum.ALL.value, docs[0]["recipientType"])
        self.assertEqual("title", docs[0]["title"])
        self.assertEqual("<p>content</p>", docs[0]["html"])
        self.assertEqual(admin_uid, docs[0]["senderId"])
        self.assertEqual([], docs[0]["batchTypeIds"])
        self.assertFalse(docs[0]["scheduled"])
        self.assertEqual(pa.second, docs[0]["publishAt"].second)

        j = scheduler.get_job("deliver_unscheduled_system_notices1")
        for _ in range(10):
            if j.finished_at is not None:
                break
            time.sleep(0.1)
        self.assertIsNotNone(j.finished_at)

        resp = self.client.get(
            "/api/managers/notices/system",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertTrue(rj["notices"][0]["scheduled"])

        self.set_access_token(u_token)
        resp = self.client.get(
            "/api/users/notices",
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)
        rj = resp.json()
        self.assertIn("system", rj)
        system_notices = rj["system"]["notices"]
        self.assertEqual(1, len(system_notices))
        sn = system_notices[0]
        self.assertEqual("title", sn["title"])
        self.assertEqual("content", sn["snippet"])

        resp = self.client.get(
            f"/api/notices/system/{sn['id']}",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual("title", rj["notice"]["title"])
        self.assertEqual("<p>content</p>", rj["notice"]["html"])

        await self.clear_default_manager(admin_uid)

    async def test_user_notice(self):
        manager_token = self.client.cookies.get(const.settings.COOKIE_ACCESS_TOKEN)

        email = "a@b.cd"
        resp = await self.create_new_temp_user(email)
        u_token = resp.cookies.get(const.settings.COOKIE_ACCESS_TOKEN)
        self.assertEqual(201, resp.status_code)

        admin_uid = await self.set_default_manager()
        self.set_access_token(manager_token)
        for i in range(3):
            pa = datetime.datetime.now(tz=utc) - datetime.timedelta(seconds=i + 1)
            resp = self.client.post(
                "/api/managers/notices/system",
                json={
                    "title": f"title{i}",
                    "content": f"content{i}",
                    "recipientType": const.notice.RecipientTypeEnum.ALL.value,
                    "batchTypeIds": [],
                    "publishAt": pa.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
                headers=self.default_headers,
            )
            self.check_ok_response(resp, 201)

        resp = self.client.get(
            "/api/managers/notices/system",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(3, rj["total"])
        self.assertEqual(3, len(rj["notices"]))

        scheduler.run_once_now(
            job_id="deliver_unscheduled_system_notices2",
            func=scheduler.tasks.notice.deliver_unscheduled_system_notices,
        )
        j = scheduler.get_job("deliver_unscheduled_system_notices2")
        for _ in range(10):
            if j.finished_at is not None:
                break
            time.sleep(0.1)
        self.assertIsNotNone(j.finished_at)
        self.assertEqual("send success 6/6 users", j.finished_return)

        self.set_access_token(u_token)
        resp = self.client.get(
            "/api/users/notices",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(3, rj["system"]["total"])
        self.assertEqual(3, len(rj["system"]["notices"]))
        for i, sn in enumerate(rj["system"]["notices"]):
            self.assertEqual(f"title{2 - i}", sn["title"])
            self.assertEqual(f"content{2 - i}", sn["snippet"])
            self.assertFalse(sn["read"])
            self.assertIsNone(sn["readTime"])

        read_id = rj["system"]['notices'][0]['id']
        resp = self.client.put(
            f"/api/users/notices/system/read/{read_id}",
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/users/notices",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(3, rj["system"]["total"])
        self.assertEqual(3, len(rj["system"]["notices"]))
        for i, sn in enumerate(rj["system"]["notices"]):
            self.assertEqual(f"title{2 - i}", sn["title"])
            self.assertEqual(f"content{2 - i}", sn["snippet"])
            if read_id == sn["id"]:
                self.assertTrue(sn["read"])
                self.assertIsNotNone(sn["readTime"])
            else:
                self.assertFalse(sn["read"])
                self.assertIsNone(sn["readTime"])

        resp = self.client.put(
            "/api/users/notices/system/read-all",
            headers=self.default_headers,
        )
        self.check_ok_response(resp, 200)

        resp = self.client.get(
            "/api/users/notices",
            headers=self.default_headers,
        )
        rj = self.check_ok_response(resp, 200)
        self.assertEqual(3, rj["system"]["total"])
        self.assertEqual(3, len(rj["system"]["notices"]))
        for i, sn in enumerate(rj["system"]["notices"]):
            self.assertEqual(f"title{2 - i}", sn["title"])
            self.assertEqual(f"content{2 - i}", sn["snippet"])
            self.assertTrue(sn["read"])
            self.assertIsNotNone(sn["readTime"])

        await self.clear_default_manager(admin_uid)
