import unittest

from rethink import models, const
from . import utils


class DataRestoreTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await models.database.drop_all()

    async def asyncTearDown(self) -> None:
        await models.database.drop_all()

    async def test_restore_search(self):
        await models.database.init()
        u, _ = await models.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.uid = u["id"]
        base_count = 2
        nids = []
        for i in range(20):
            n, code = await models.node.add(
                uid=self.uid,
                md=f"title{i}\ntext{i}",
                type_=const.NodeType.MARKDOWN.value,
            )
            nids.append(n["id"])
            self.assertEqual(const.Code.OK, code)
        self.assertEqual(20 + base_count, await models.database.searcher().count_all())

        code = await models.node.batch_to_trash(uid=self.uid, nids=nids[:10])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(20 + base_count, await models.database.searcher().count_all())

        code = await models.database.searcher().delete_batch(
            uid=self.uid,
            nids=nids[:10],
        )
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(10 + base_count, await models.database.searcher().count_all())

        await models.database.init()
        self.assertEqual(20 + base_count, await models.database.searcher().count_all())
