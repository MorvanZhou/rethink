import datetime
import time
import unittest

from bson import ObjectId

from retk import const
from retk.models.search_engine.engine_local import LocalSearcher, SearchDoc
from retk.models.tps import AuthedUser
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
        self.au = AuthedUser(
            u=AuthedUser.User(
                _id=ObjectId(),
                id="uid",
                source=0,
                account="rethink",
                nickname="rethink",
                email="rethink@rethink.run",
                avatar="",
                hashed="",
                disabled=False,
                modified_at=datetime.datetime.now(),
                used_space=0,
                type=0,

                last_state=AuthedUser.User.LastState(
                    node_display_method=0,
                    node_display_sort_key="",
                    recent_search=[],
                    recent_cursor_search_selected_nids=[],
                ),
                settings=AuthedUser.User.Settings(
                    language="en",
                    theme="light",
                    editor_mode="markdown",
                    editor_font_size=14,
                    editor_code_theme="github",
                    editor_sep_right_width=0,
                    editor_side_current_tool_id="",
                ),
            ),
            language="en",
            request_id="request_id",
        )

    async def asyncTearDown(self) -> None:
        await self.searcher.drop()

    async def test_add(self):
        for i in range(20):
            code = await self.searcher.add(au=self.au, doc=SearchDoc(
                nid=f"nid{i}",
                title=f"title {i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ))
            self.assertEqual(const.CodeEnum.OK, code)
            time.sleep(0.0001)

        docs, total = await self.searcher.search(
            au=self.au,
            query="title doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            limit=10,
        )

        self.assertEqual(10, len(docs))
        self.assertEqual(20, total)
        self.assertEqual("nid19", docs[0].nid)
        self.assertEqual("nid10", docs[-1].nid)
        self.assertEqual(['19 <em class="match term1">doc</em>, 这是第 19 个文档'], docs[0].bodyHighlights)
        self.assertEqual("<em class=\"match term0\">title</em> 19", docs[0].titleHighlight)

        docs, total = await self.searcher.search(
            au=self.au,
            query="doc",
            page=200,
            limit=10,
        )
        self.assertEqual(0, len(docs))
        self.assertEqual(20, total)

        docs, total = await self.searcher.search(
            au=self.au,
            query="",
            page=0,
            limit=50,
        )
        self.assertEqual(20, len(docs))
        self.assertEqual(20, total)

        count = await self.searcher.count_all()
        self.assertEqual(20, count)

    async def test_batch_add_update_delete(self):
        code = await self.searcher.add_batch(au=self.au, docs=[
            SearchDoc(
                nid=f"nid{i}",
                title=f"title{i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ) for i in range(20)
        ])
        self.assertEqual(const.CodeEnum.OK, code)

        docs, total = await self.searcher.search(
            au=self.au,
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            limit=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(20, total)

        code = await self.searcher.update_batch(au=self.au, docs=[
            SearchDoc(
                nid=f"nid{i}",
                title=f"title_update{i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ) for i in range(20)
        ])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(20, await self.searcher.count_all())

        docs, total = await self.searcher.search(
            au=self.au,
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            limit=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(20, total)
        self.assertEqual("nid19", docs[0].nid)

        code = await self.searcher.disable(au=self.au, nid="nid18")
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(20, await self.searcher.count_all())

        docs, total = await self.searcher.search(
            au=self.au,
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            limit=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(19, total)
        self.assertEqual("nid17", docs[1].nid)
        self.assertEqual(20, await self.searcher.count_all())

        code = await self.searcher.enable(au=self.au, nid="nid18")
        self.assertEqual(const.CodeEnum.OK, code)

        code = await self.searcher.batch_to_trash(au=self.au, nids=[f"nid{i}" for i in range(10)])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(20, await self.searcher.count_all())
        code = await self.searcher.delete_batch(au=self.au, nids=[f"nid{i}" for i in range(10)])
        self.assertEqual(const.CodeEnum.OK, code)
        self.assertEqual(10, await self.searcher.count_all())

        docs, total = await self.searcher.search(
            au=self.au,
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            limit=10,
        )
        self.assertEqual(10, len(docs))
        self.assertEqual(10, total)
        self.assertEqual("nid19", docs[0].nid)
        self.assertEqual("nid18", docs[1].nid)
        self.assertEqual("nid17", docs[2].nid)

        docs, total = await self.searcher.search(
            au=self.au,
            query="doc",
            sort_key="createdAt",
            reverse=True,
            page=0,
            limit=10,
            exclude_nids=["nid19"]
        )
        self.assertEqual(9, len(docs))
        self.assertEqual(9, total)
        self.assertEqual("nid18", docs[0].nid)

        docs, total = await self.searcher.search(
            au=self.au,
            query="doc",
            sort_key="title",
            reverse=False,
            page=0,
            limit=10,
            exclude_nids=["nid19"]
        )
        self.assertEqual(9, len(docs))
        self.assertEqual(9, total)
        self.assertEqual("nid10", docs[0].nid)
