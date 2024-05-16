import datetime
import unittest

import elastic_transport
from bson import ObjectId
from bson.tz_util import utc

from retk import const, config
from retk.models.search_engine.engine_es import ESSearcher, SearchDoc
from retk.models.tps import AuthedUser
from . import utils


class ESTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.dev")
        cls.searcher = ESSearcher()

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.dev")

    async def asyncSetUp(self) -> None:
        if utils.skip_no_connect.skip:
            print("remote test asyncSetUp skipped")
            return
        try:
            await self.searcher.drop()
            await self.searcher.init()
            self.assertTrue(await self.searcher.es.indices.exists(index=config.get_settings().ES_INDEX_ALIAS))
        except (elastic_transport.ConnectionError, RuntimeError):
            utils.skip_no_connect.skip = True
            print("remote test asyncSetUp timeout")
            if self.searcher.es is not None:
                await self.searcher.es.close()
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
                modified_at=datetime.datetime.now(tz=utc),
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
        if utils.skip_no_connect.skip:
            print("remote test asyncTearDown skipped")
            return
        try:
            await self.searcher.drop()
        except (elastic_transport.ConnectionError, RuntimeError):
            pass

    @utils.skip_no_connect
    async def test_reindex(self):
        code = await self.searcher.add_batch(au=self.au, docs=[SearchDoc(
            nid=f"nid{i}",
            title=f"title{i}",
            body=f"this is {i} doc, 这是第 {i} 个文档",
        ) for i in range(20)])
        self.assertEqual(const.CodeEnum.OK, code)
        await self.searcher.refresh()
        self.assertIn(config.get_settings().ES_INDEX_ALIAS, self.searcher.index)
        self.assertEqual("1", self.searcher.index.split("-")[-1])

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

        await self.searcher.reindex()
        await self.searcher.refresh()
        self.assertEqual(20, await self.searcher.count_all())
        self.assertIn(config.get_settings().ES_INDEX_ALIAS, self.searcher.index)
        self.assertEqual("2", self.searcher.index.split("-")[-1])

    @utils.skip_no_connect
    async def test_add(self):
        for i in range(20):
            code = await self.searcher.add(au=self.au, doc=SearchDoc(
                nid=f"nid{i}",
                title=f"title{i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ))
            self.assertEqual(const.CodeEnum.OK, code)

        await self.searcher.refresh()
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
        self.assertEqual(['this is 19 <em class="match term0">doc</em>, 这是第 19 个文档'], docs[0].bodyHighlights)

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
        self.assertEqual([], docs[0].bodyHighlights)

        count = await self.searcher.count_all()
        self.assertEqual(20, count)

    @utils.skip_no_connect
    async def test_batch_add_update_delete(self):
        code = await self.searcher.add_batch(au=self.au, docs=[
            SearchDoc(
                nid=f"nid{i}",
                title=f"title{i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ) for i in range(20)
        ])
        self.assertEqual(const.CodeEnum.OK, code)
        await self.searcher.refresh()
        count = await self.searcher.count_all()
        self.assertEqual(20, count)

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

        code = await self.searcher.update_batch(au=self.au, docs=[
            SearchDoc(
                nid=f"nid{i}",
                title=f"title_update{i}",
                body=f"this is {i} doc, 这是第 {i} 个文档",
            ) for i in range(20)
        ])
        self.assertEqual(const.CodeEnum.OK, code)
        await self.searcher.refresh()
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

    @utils.skip_no_connect
    async def test_multi_user(self):

        for uid in ["uid1", "uid2"]:
            self.au.u.id = uid
            code = await self.searcher.add_batch(au=self.au, docs=[
                SearchDoc(
                    nid=f"{uid}nid{i}",
                    title=f"title{i}",
                    body=f"this is {i} doc, 这是第 {i} 个文档",
                ) for i in range(20)
            ])
            self.assertEqual(const.CodeEnum.OK, code)

        await self.searcher.refresh()

        for uid in ["uid1", "uid2"]:
            self.au.u.id = uid
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
            self.assertEqual(f"{uid}nid19", docs[0].nid)
