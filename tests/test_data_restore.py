import unittest

from retk import const, core
from retk.models.client import client
from retk.models.tps import AuthedUser, convert_user_dict_to_authed_user
from . import utils


class DataRestoreTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await client.init()

    async def asyncTearDown(self) -> None:
        await client.drop()

    async def test_restore_search(self):
        u, _ = await core.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.au = AuthedUser(
            u=convert_user_dict_to_authed_user(u),
            request_id="test",
            language=const.LanguageEnum.EN.value,
        )
        base_count = 2
        nids = []
        for i in range(20):
            n, code = await core.node.post(
                au=self.au,
                md=f"title{i}\ntext{i}",
                type_=const.NodeTypeEnum.MARKDOWN.value,
            )
            nids.append(n["id"])
            self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(20 + base_count, await client.search.count_all())

        code = await core.node.batch_to_trash(au=self.au, nids=nids[:10])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(20 + base_count, await client.search.count_all())

        code = await client.search.delete_batch(
            au=self.au,
            nids=nids[:10],
        )
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(10 + base_count, await client.search.count_all())

        await client.init()
        self.assertEqual(20 + base_count, await client.search.count_all())
