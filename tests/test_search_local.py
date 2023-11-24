import unittest

from rethink.models.search.engine_local import LocalSearcher, SearchDoc
from . import utils


class LocalSearchTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")
        cls.searcher = LocalSearcher()

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    async def asyncSetUp(self) -> None:
        await self.searcher.drop()
        await self.searcher.init()
        self.assertTrue(self.searcher.index_path.exists())

    async def asyncTearDown(self) -> None:
        await self.searcher.drop()
        self.assertFalse(self.searcher.index_path.exists())

    async def test_add(self):
        for i in range(20):
            await self.searcher.add(uid="uid", doc=SearchDoc(
                nid=f"nid{i}",
                title=f"title{i}",
                md=f"this is {i} doc, 这是第 {i} 个文档",
            ))

        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=1,
            page_size=10,
        )

        self.assertEqual(10, len(docs))
        self.assertEqual(20, total)
        self.assertEqual("nid19", docs[0].nid)
        self.assertEqual("nid10", docs[-1].nid)
        self.assertEqual("title19", docs[0].title)
        self.assertEqual('19 <b class="match term0">doc</b>, 这是第 19 个文档', docs[0].highlights)

        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            page=200,
            page_size=10,
        )
        self.assertEqual(0, len(docs))
        self.assertEqual(20, total)

    async def test_batch_add_update_delete(self):
        await self.searcher.add_batch(uid="uid", docs=[
            SearchDoc(
                nid=f"nid{i}",
                title=f"title{i}",
                md=f"this is {i} doc, 这是第 {i} 个文档",
            ) for i in range(20)
        ])
        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=1,
            page_size=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(20, total)
        self.assertEqual(docs[0].createdAt, docs[0].modifiedAt)

        await self.searcher.update_batch(uid="uid", docs=[
            SearchDoc(
                nid=f"nid{i}",
                title=f"title_update{i}",
                md=f"this is {i} doc, 这是第 {i} 个文档",
            ) for i in range(20)
        ])
        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=1,
            page_size=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(20, total)
        self.assertEqual("title_update19", docs[0].title)
        self.assertNotEqual(docs[0].createdAt, docs[0].modifiedAt)

        await self.searcher.delete_batch(uid="uid", nids=[f"nid{i}" for i in range(10)])
        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=1,
            page_size=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(10, total)
        self.assertEqual("title_update19", docs[0].title)
