import unittest
from io import BytesIO

from rethink import const
from rethink.core.verify import verification
from rethink.models.client import client
from rethink.utils import jwt_decode
from . import utils


class VerificationTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await client.drop()

    def test_verification_img(self):
        token, data = verification.random_captcha()
        self.assertIsInstance(token, str)
        self.assertIn("img", data)
        self.assertIsInstance(data["img"], BytesIO)
        self.assertNotIn("sound", data)

    def test_verify_img(self):
        token, data = verification.random_captcha()
        decoded = jwt_decode(token)
        code = verification.verify_captcha(token=token, code_str=decoded["code"])
        self.assertEqual(const.Code.OK, code)

        code = verification.verify_captcha(token=token, code_str="1234")
        self.assertEqual(const.Code.CAPTCHA_ERROR, code)
