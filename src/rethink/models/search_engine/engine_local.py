import datetime
import logging
from typing import List, Tuple, Sequence, Literal

import jieba
from bson.tz_util import utc
from jieba.analyse import ChineseAnalyzer
from whoosh.fields import TEXT, ID, Schema, DATETIME, BOOLEAN
from whoosh.highlight import Highlighter, HtmlFormatter
from whoosh.index import create_in, open_dir, FileIndex
from whoosh.qparser import QueryParser, syntax
from whoosh.query import Term, And, Or, Every

from rethink import config, const
from rethink.logger import logger
from rethink.models.search_engine.engine import (
    BaseEngine, SearchDoc, SearchResult, RestoreSearchDoc, STOPWORDS,
)

jieba.setLogLevel(logging.ERROR)


class LocalSearcher(BaseEngine):
    ix: FileIndex
    indexing_schema: Schema
    search_stop_schema: Schema

    async def _trash_disable_ops_batch(
            self,
            uid: str,
            nids: List[str],
            disable: bool = None,
            in_trash: bool = None
    ) -> const.Code:
        writer = self.ix.writer()
        for nid in nids:
            with self.ix.searcher() as searcher:
                resp = searcher.search(And([Term("uid", uid), Term("nid", nid)]))
                if len(resp) != 1:
                    logger.error(f"nid {nid} not found or more than one found")
                    return const.Code.NODE_NOT_EXIST
                res = resp[0]
                new = {
                    "createdAt": res["createdAt"],
                    "nid": nid,
                    "modifiedAt": res["modifiedAt"],
                    "title": res["title"],
                    "body": res["body"],
                    "disabled": disable if disable is not None else res["disabled"],
                    "inTrash": in_trash if in_trash is not None else res["inTrash"],
                }

            writer.update_document(uid=uid, **new)
        writer.commit()
        return const.Code.OK

    @property
    def index_path(self):
        return config.get_settings().LOCAL_STORAGE_PATH / ".data" / "search"

    async def init(self):
        def create_schema(analyzer):
            return Schema(
                uid=ID(stored=True),
                nid=ID(stored=True, unique=True),
                title=TEXT(analyzer=analyzer, stored=True, sortable=True),
                body=TEXT(analyzer=analyzer, stored=True),
                disabled=BOOLEAN(stored=True),
                inTrash=BOOLEAN(stored=True),
                modifiedAt=DATETIME(stored=True, sortable=True),
                createdAt=DATETIME(stored=True, sortable=True),
            )

        self.indexing_schema = create_schema(analyzer=ChineseAnalyzer())
        self.search_stop_schema = create_schema(analyzer=ChineseAnalyzer(stoplist=STOPWORDS))

        if not self.index_path.exists():
            self.index_path.mkdir(parents=True)
            self.ix = create_in(self.index_path, self.indexing_schema)
        else:
            self.ix = open_dir(self.index_path)

    async def drop(self):
        try:
            w = self.ix.writer()
            w.delete_by_query(Every("nid"))
            w.commit()
            self.ix.close()
        except (AttributeError, FileNotFoundError):
            pass
        # # remove all index
        # if self.index_path.exists():
        #     rmtree(self.index_path)

    async def add(self, uid: str, doc: SearchDoc) -> const.Code:
        return await self.add_batch(uid=uid, docs=[doc])

    async def update(self, uid: str, doc: SearchDoc) -> const.Code:
        return await self.update_batch(uid=uid, docs=[doc])

    async def to_trash(self, uid: str, nid: str) -> const.Code:
        return await self.batch_to_trash(uid=uid, nids=[nid])

    async def restore_from_trash(self, uid: str, nid: str) -> const.Code:
        return await self.restore_batch_from_trash(uid=uid, nids=[nid])

    async def disable(self, uid: str, nid: str) -> const.Code:
        return await self._trash_disable_ops_batch(uid=uid, nids=[nid], disable=True)

    async def enable(self, uid: str, nid: str) -> const.Code:
        return await self._trash_disable_ops_batch(uid=uid, nids=[nid], disable=False)

    async def delete(self, uid: str, nid: str) -> const.Code:
        return await self.delete_batch(uid=uid, nids=[nid])

    async def add_batch(self, uid: str, docs: List[SearchDoc]) -> const.Code:
        writer = self.ix.writer()
        now = datetime.datetime.now(tz=utc)
        for doc in docs:
            d = doc.__dict__
            now_ = datetime.datetime.now(tz=utc)
            delta = datetime.timedelta(microseconds=100)
            if now + delta >= now_:
                now_ = now + delta
            d["createdAt"] = now_
            d["modifiedAt"] = d["createdAt"]
            d["disabled"] = False
            d["inTrash"] = False
            writer.add_document(uid=uid, **d)
            now = now_

        writer.commit()
        return const.Code.OK

    async def batch_to_trash(self, uid: str, nids: List[str]) -> const.Code:
        return await self._trash_disable_ops_batch(uid=uid, nids=nids, in_trash=True)

    async def restore_batch_from_trash(self, uid: str, nids: List[str]) -> const.Code:
        return await self._trash_disable_ops_batch(uid=uid, nids=nids, in_trash=False)

    async def delete_batch(self, uid: str, nids: List[str]) -> const.Code:
        writer = self.ix.writer()
        for nid in nids:
            q = And([Term("uid", uid), Term("nid", nid), Term("inTrash", True)])
            count = writer.delete_by_query(q=q)
            if count != 1:
                logger.error(f"nid {nid} not found or more than one found")
                return const.Code.NODE_NOT_EXIST
        writer.commit()
        return const.Code.OK

    async def update_batch(self, uid: str, docs: List[SearchDoc]) -> const.Code:
        writer = self.ix.writer()
        for doc in docs:
            with self.ix.searcher() as searcher:
                resp = searcher.search(And([Term("uid", uid), Term("nid", doc.nid)]))
                if len(resp) != 1:
                    logger.error(f"nid {doc.nid} not found or more than one found")
                    return const.Code.NODE_NOT_EXIST
                res = resp[0]
                new = {
                    "createdAt": res["createdAt"],
                    "nid": doc.nid,
                    "modifiedAt": datetime.datetime.now(tz=utc),
                    "title": doc.title if doc.title != "" else res["title"],
                    "body": doc.body if doc.body != "" else res["body"],
                    "disabled": res["disabled"],
                    "inTrash": res["inTrash"],
                }
            writer.update_document(uid=uid, **new)
        writer.commit()
        return const.Code.OK

    async def _search(
            self,
            uid: str,
            query: str = "",
            sort_key: Literal[
                "createdAt", "modifiedAt", "title", "similarity"
            ] = None,
            reverse: bool = False,
            page: int = 0,
            page_size: int = 10,
            exclude_nids: Sequence[str] = None,
            with_stop_analyzer: bool = False,
    ) -> Tuple[List[SearchResult], int]:
        if sort_key in ["", "similarity"]:
            sort_key = None
        with self.ix.searcher() as searcher:
            cs = [Term("uid", uid), Term("disabled", False), Term("inTrash", False)]
            if query != "":
                schema = self.search_stop_schema if with_stop_analyzer else self.indexing_schema
                q_body = QueryParser("body", schema, group=syntax.OrGroup).parse(query.lower())
                q_title = QueryParser("title", schema, group=syntax.OrGroup).parse(query.lower())
                cs.append(Or([q_body, q_title]))
            query_terms = And(cs)
            if exclude_nids is not None and len(exclude_nids) > 0:
                mask = Term("nid", exclude_nids)
            else:
                mask = None
            hits = searcher.search_page(
                query=query_terms,
                pagenum=page + 1,
                pagelen=page_size,
                sortedby=sort_key,
                reverse=reverse,
                mask=mask,
            )
            if page * page_size > hits.total:
                return [], hits.total
            hl = Highlighter(formatter=HtmlFormatter(
                tagname=self.hl_tag_name,
                classname=self.hl_class_name,
                termclass=self.hl_term_prefix
            ))

            return [
                SearchResult(
                    nid=hit["nid"],
                    score=hit.score if sort_key != "title" else 0.,
                    titleHighlight=self.get_hl(hl, hit, "title", return_list=False, default=hit["title"]),
                    bodyHighlights=self.get_hl(hl, hit, "body", return_list=True, default=hit["body"][:60] + "..."),
                ) for hit in hits
            ], hits.total

    async def search(
            self,
            uid: str,
            query: str = "",
            sort_key: Literal[
                "createdAt", "modifiedAt", "title", "similarity"
            ] = None,
            reverse: bool = False,
            page: int = 0,
            page_size: int = 10,
            exclude_nids: Sequence[str] = None,
    ) -> Tuple[List[SearchResult], int]:
        return await self._search(
            uid=uid,
            query=query,
            sort_key=sort_key,
            reverse=reverse,
            page=page,
            page_size=page_size,
            exclude_nids=exclude_nids,
            with_stop_analyzer=False,
        )

    async def recommend(
            self,
            uid: str,
            content: str,
            max_return: int = 10,
            exclude_nids: Sequence[str] = None,
    ) -> List[SearchResult]:
        threshold = 5.
        res, total = await self._search(
            uid=uid,
            query=content,
            sort_key="similarity",
            reverse=True,
            page=0,
            page_size=max_return,
            exclude_nids=exclude_nids,
            with_stop_analyzer=True,
        )
        return [r for r in res if r.score >= threshold]

    async def refresh(self):
        raise NotImplementedError

    async def count_all(self) -> int:
        with self.ix.searcher() as searcher:
            resp = searcher.search(Every("nid"))
            return len(resp)

    async def batch_restore_docs(self, uid: str, docs: List[RestoreSearchDoc]) -> const.Code:
        writer = self.ix.writer()
        for doc in docs:
            writer.add_document(uid=uid, **doc.__dict__)
        writer.commit()
        return const.Code.OK

    @staticmethod
    def get_hl(hl: Highlighter, hit: dict, key: str, return_list: bool, default: str = ""):
        hl_str = hl.highlight_hit(hit, key)
        if return_list:
            if hl_str == "":
                return [default]
            return [hl_str]
        if hl_str == "":
            return default
        return hl_str
