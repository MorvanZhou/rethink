import unittest

import elastic_transport

from rethink import const
from rethink.models.search_engine.engine_es import ESSearcher, SearchDoc
from . import utils


class ESTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skip = False
        utils.set_env(".env.test.development")
        cls.searcher = ESSearcher()

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.development")

    async def asyncSetUp(self) -> None:
        if self.skip:
            return
        try:
            await self.searcher.drop()
            await self.searcher.init()
            self.assertTrue(await self.searcher.es.indices.exists(index=self.searcher.index_name))
        except elastic_transport.ConnectionError:
            self.skip = True

    async def asyncTearDown(self) -> None:
        if self.skip:
            return
        await self.searcher.drop()

    @utils.skip_no_connect
    async def test_add(self):
        for i in range(20):
            code = await self.searcher.add(uid="uid", doc=SearchDoc(
                nid=f"nid{i}",
                title=f"title{i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ))
            self.assertEqual(const.Code.OK, code)

        await self.searcher.refresh()
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
        self.assertEqual(['this is 19 <em class="match term0">doc</em>, 这是第 19 个文档'], docs[0].bodyHighlights)

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
        self.assertEqual([], docs[0].bodyHighlights)

    @utils.skip_no_connect
    async def test_batch_add_update_delete(self):
        code = await self.searcher.add_batch(uid="uid", docs=[
            SearchDoc(
                nid=f"nid{i}",
                title=f"title{i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ) for i in range(20)
        ])
        self.assertEqual(const.Code.OK, code)
        await self.searcher.refresh()

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

        code = await self.searcher.update_batch(uid="uid", docs=[
            SearchDoc(
                nid=f"nid{i}",
                title=f"title_update{i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ) for i in range(20)
        ])
        self.assertEqual(const.Code.OK, code)
        await self.searcher.refresh()

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
        await self.searcher.refresh()
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

        code = await self.searcher.enable(uid="uid", nid="nid18")
        self.assertEqual(const.Code.OK, code)

        code = await self.searcher.batch_to_trash(uid="uid", nids=[f"nid{i}" for i in range(10)])
        self.assertEqual(const.Code.OK, code)
        await self.searcher.refresh()

        code = await self.searcher.delete_batch(uid="uid", nids=[f"nid{i}" for i in range(10)])
        self.assertEqual(const.Code.OK, code)
        await self.searcher.refresh()
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

    @utils.skip_no_connect
    async def test_multi_user(self):
        for uid in ["uid1", "uid2"]:
            code = await self.searcher.add_batch(uid=uid, docs=[
                SearchDoc(
                    nid=f"{uid}nid{i}",
                    title=f"title{i}",
                    body=f"this is {i} doc, 这是第 {i} 个文档",
                ) for i in range(20)
            ])
            self.assertEqual(const.Code.OK, code)

        await self.searcher.refresh()

        for uid in ["uid1", "uid2"]:
            docs, total = await self.searcher.search(
                uid=uid,
                query="doc",
                sort_key="createdAt",
                reverse=True,
                page=0,
                page_size=10,
            )
            self.assertEqual(10, len(docs))
            self.assertEqual(20, total)
            self.assertEqual(f"{uid}nid19", docs[0].nid)