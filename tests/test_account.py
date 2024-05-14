import unittest
from io import BytesIO

import bcrypt

from retk import const, regex
from retk.core import account, user
from retk.models.client import client
from retk.models.tps import convert_user_dict_to_authed_user
from retk.utils import jwt_decode
from . import utils


class AccountTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        utils.set_env(".env.test.local")
        cls.salt = bcrypt.gensalt(rounds=5)

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await client.drop()
        await client.init()

    def test_verify(self):
        password = "123abc"
        email = "rethink@rethink.run"
        bpw = account.manager._base_password(password=password, email=email)
        token_str = bcrypt.hashpw(bpw, self.salt).decode("utf-8")
        self.assertEqual(60, len(token_str))
        hashed = account.manager._base_password(password=password, email=email)
        match = bcrypt.checkpw(hashed, token_str.encode("utf-8"))
        self.assertTrue(match)

    def test_hash(self):
        pwd = "123abc&&rethink@rethink.run"
        pwd_bt = pwd.encode("utf-8")
        hashed = bcrypt.hashpw(pwd_bt, self.salt)
        # print(hashed)
        match = bcrypt.checkpw(pwd_bt, hashed)
        self.assertTrue(match)

    async def test_one_user(self):
        u, code = await account.manager.signup("a@q.com", "rethink", const.LanguageEnum.EN.value)
        self.assertEqual(const.CodeEnum.ONE_USER_MODE, code)
        self.assertIsNone(u)

    async def test_verify_user(self):
        u, err = await user.get_by_email("rethink@rethink.run")
        self.assertEqual(const.CodeEnum.OK, err)
        self.assertIsNotNone(u)
        au = convert_user_dict_to_authed_user(u)
        ok = await account.manager.is_right_password(
            email=au.email,
            hashed=au.hashed,
            password="rethink"
        )
        self.assertTrue(ok)

    def test_valid_password(self):
        for t, b in [
            ("rethink", False),
            ("123334", False),
            ("ret123", True),
            ("re123", False),
            ("rethink123", True),
            ("sd@d", False),
            ("sd@d123", True),
            ("1s", False),
            ("", False)
        ]:
            if b:
                self.assertIsNotNone(regex.VALID_PASSWORD.match(t), msg=t)
            else:
                self.assertIsNone(regex.VALID_PASSWORD.match(t), msg=t)

    def test_salt(self):
        npw = "12345"
        self.assertLessEqual(len(npw), const.settings.PASSWORD_MAX_LENGTH)
        bpw = account.manager._base_password(password=npw, email="rethink@rethink.run")
        salt = bcrypt.gensalt()
        hpw = bcrypt.hashpw(bpw, salt).decode("utf-8")
        self.assertEqual(salt.decode("utf-8"), hpw[:len(salt)])
        self.assertNotEqual(bpw.decode("utf-8"), hpw[len(salt):])

    def test_verification_img(self):
        token, data = account.app_captcha.generate()
        self.assertIsInstance(token, str)
        self.assertIn("img", data)
        self.assertIsInstance(data["img"], BytesIO)
        self.assertNotIn("sound", data)

    def test_verify_img(self):
        token, _ = account.app_captcha.generate()
        decoded = jwt_decode(token)
        code = account.app_captcha.verify_captcha(token=token, code_str=decoded["code"])
        self.assertEqual(const.CodeEnum.OK, code)

        code = account.app_captcha.verify_captcha(token=token, code_str="1234")
        self.assertEqual(const.CodeEnum.CAPTCHA_ERROR, code)
