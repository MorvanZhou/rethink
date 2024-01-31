import unittest

from rethink import const, core
from rethink.models.client import client
from . import utils


class DataRestoreTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await client.drop()

    async def asyncTearDown(self) -> None:
        await client.drop()

    async def test_restore_search(self):
        await client.init()
        u, _ = await core.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.uid = u["id"]
        base_count = 2
        nids = []
        for i in range(20):
            n, code = await core.node.add(
                uid=self.uid,
                md=f"title{i}\ntext{i}",
                type_=const.NodeType.MARKDOWN.value,
            )
            nids.append(n["id"])
            self.assertEqual(const.Code.OK, code)
        self.assertEqual(20 + base_count, await client.search.count_all())

        code = await core.node.batch_to_trash(uid=self.uid, nids=nids[:10])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(20 + base_count, await client.search.count_all())

        code = await client.search.delete_batch(
            uid=self.uid,
            nids=nids[:10],
        )
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(10 + base_count, await client.search.count_all())

        await client.init()
        self.assertEqual(20 + base_count, await client.search.count_all())
