import unittest

import bcrypt

from rethink import const, regex
from rethink.controllers import auth
from rethink.models import database
from . import utils


class AuthTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        utils.set_env(".env.test.local")
        cls.salt = bcrypt.gensalt(rounds=5)

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await database.drop_all()
        await database.init()

    def test_verify(self):
        password = "123abc"
        email = "rethink@rethink.run"
        bpw = auth._base_password(password=password, email=email)
        token_str = bcrypt.hashpw(bpw, self.salt).decode("utf-8")
        self.assertEqual(60, len(token_str))
        hashed = auth._base_password(password=password, email=email)
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
        uid, code = await auth.register_user("a@q.com", "rethink", const.Language.EN.value)
        self.assertEqual(const.Code.ONE_USER_MODE, code)
        self.assertEqual("", uid)

    async def test_verify_user(self):
        u, err = await auth.get_user_by_email("rethink@rethink.run")
        self.assertEqual(const.Code.OK, err)
        ok = await auth.verify_user(u, "rethink")
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
                self.assertIsNotNone(regex.VALID_PASSWORD_PTN.match(t), msg=t)
            else:
                self.assertIsNone(regex.VALID_PASSWORD_PTN.match(t), msg=t)
