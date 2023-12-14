import time
import unittest

from rethink import const
from rethink.models.search_engine.engine_local import LocalSearcher, SearchDoc
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

    async def test_add(self):
        for i in range(20):
            code = await self.searcher.add(uid="uid", doc=SearchDoc(
                nid=f"nid{i}",
                title=f"title {i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ))
            self.assertEqual(const.Code.OK, code)
            time.sleep(0.0001)

        docs, total = await self.searcher.search(
            uid="uid",
            query="title doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            page_size=10,
        )

        self.assertEqual(10, len(docs))
        self.assertEqual(20, total)
        self.assertEqual("nid19", docs[0].nid)
        self.assertEqual("nid10", docs[-1].nid)
        self.assertEqual(['19 <em class="match term1">doc</em>, 这是第 19 个文档'], docs[0].bodyHighlights)
        self.assertEqual("<em class=\"match term0\">title</em> 19", docs[0].titleHighlight)

        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            page=200,
            page_size=10,
        )
        self.assertEqual(0, len(docs))
        self.assertEqual(20, total)

        docs, total = await self.searcher.search(
            uid="uid",
            query="",
            page=0,
            page_size=50,
        )
        self.assertEqual(20, len(docs))
        self.assertEqual(20, total)

        count = await self.searcher.count_all()
        self.assertEqual(20, count)

    async def test_batch_add_update_delete(self):
        code = await self.searcher.add_batch(uid="uid", docs=[
            SearchDoc(
                nid=f"nid{i}",
                title=f"title{i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ) for i in range(20)
        ])
        self.assertEqual(const.Code.OK, code)

        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            page_size=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(20, total)

        code = await self.searcher.update_batch(uid="uid", docs=[
            SearchDoc(
                nid=f"nid{i}",
                title=f"title_update{i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ) for i in range(20)
        ])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(20, await self.searcher.count_all())

        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            page_size=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(20, total)
        self.assertEqual("nid19", docs[0].nid)

        code = await self.searcher.disable(uid="uid", nid="nid18")
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(20, await self.searcher.count_all())

        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            page_size=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(19, total)
        self.assertEqual("nid17", docs[1].nid)
        self.assertEqual(20, await self.searcher.count_all())

        code = await self.searcher.enable(uid="uid", nid="nid18")
        self.assertEqual(const.Code.OK, code)

        code = await self.searcher.batch_to_trash(uid="uid", nids=[f"nid{i}" for i in range(10)])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(20, await self.searcher.count_all())
        code = await self.searcher.delete_batch(uid="uid", nids=[f"nid{i}" for i in range(10)])
        self.assertEqual(const.Code.OK, code)
        self.assertEqual(10, await self.searcher.count_all())

        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            page_size=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(10, total)
        self.assertEqual("nid19", docs[0].nid)
        self.assertEqual("nid18", docs[1].nid)
        self.assertEqual("nid17", docs[2].nid)

        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            page_size=10,
            exclude_nids=[f"nid19"]
        )
        self.assertEqual(9, len(docs))
        self.assertEqual(9, total)
        self.assertEqual("nid18", docs[0].nid)

        docs, total = await self.searcher.search(
            uid="uid",
            query="doc",
            sort_key="title",
            reverse=False,
            page=0,
            page_size=10,
            exclude_nids=[f"nid19"]
        )
        self.assertEqual(9, len(docs))
        self.assertEqual(9, total)
        self.assertEqual("nid10", docs[0].nid)
