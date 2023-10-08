import unittest

import bcrypt

from rethink import const
from rethink.controllers import auth
from rethink.models import database
from . import utils


class AuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        utils.set_env(".env.test.local")
        database.init()
        cls.salt = bcrypt.gensalt(rounds=5)

    @classmethod
    def tearDownClass(cls) -> None:
        database.drop_all()
        utils.drop_env(".env.test.local")

    def test_verify(self):
        password = "123abc"
        email = "rethink@rethink.com"
        bpw = auth._base_password(password=password, email=email)
        token_str = bcrypt.hashpw(bpw, self.salt).decode("utf-8")
        hashed = auth._base_password(password=password, email=email)
        match = bcrypt.checkpw(hashed, token_str.encode("utf-8"))
        self.assertTrue(match)

    def test_hash(self):
        pwd = "123abc&&rethink@rethink.com"
        pwd_bt = pwd.encode("utf-8")
        hashed = bcrypt.hashpw(pwd_bt, self.salt)
        # print(hashed)
        match = bcrypt.checkpw(pwd_bt, hashed)
        self.assertTrue(match)

    def test_verify_user(self):
        u, err = auth.get_user_by_email("rethink@rethink.com")
        self.assertEqual(const.Code.OK, err)
        ok = auth.verify_user(u, "rethink")
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
                self.assertIsNotNone(auth.VALID_PASSWORD_PTN.match(t), msg=t)
            else:
                self.assertIsNone(auth.VALID_PASSWORD_PTN.match(t), msg=t)
