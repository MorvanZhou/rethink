import datetime
from pathlib import Path
from shutil import rmtree
from typing import List, Tuple

from bson.tz_util import utc
from jieba.analyse import ChineseAnalyzer
from whoosh.fields import TEXT, ID, Schema, DATETIME
from whoosh.highlight import Highlighter, HtmlFormatter
from whoosh.index import create_in, open_dir, FileIndex
from whoosh.qparser import QueryParser
from whoosh.query import Term, And

from rethink import config
from rethink.models.search.engine import BaseEngine, SearchDoc, SearchResult


class LocalSearcher(BaseEngine):
    ix: FileIndex

    @property
    def index_path(self):
        return config.get_settings().LOCAL_STORAGE_PATH / ".data" / "search"

    async def init(self):
        if not self.index_path.exists():
            self.index_path.mkdir(parents=True)
            analyzer = ChineseAnalyzer(
                stoplist=(Path(__file__).parent / "stop_words.txt").read_text().splitlines(),
            )
            schema = Schema(
                uid=ID(stored=True),
                nid=ID(stored=True, unique=True),
                title=TEXT(stored=True, sortable=True),
                md=TEXT(analyzer=analyzer, stored=True),
                modifiedAt=DATETIME(stored=True, sortable=True),
                createdAt=DATETIME(stored=True, sortable=True),
            )
            self.ix = create_in(self.index_path, schema)
        else:
            self.ix = open_dir(self.index_path)

    async def drop(self):
        # remove all index
        rmtree(self.index_path, ignore_errors=True)
        try:
            self.ix.close()
        except AttributeError:
            pass

    async def add(self, uid: str, doc: SearchDoc):
        return await self.add_batch(uid=uid, docs=[doc])

    async def update(self, uid: str, doc: SearchDoc):
        return await self.update_batch(uid=uid, docs=[doc])

    async def delete(self, uid: str, nid: str):
        return await self.delete_batch(uid=uid, nids=[nid])

    async def add_batch(self, uid: str, docs: List[SearchDoc]):
        writer = self.ix.writer()
        for doc in docs:
            d = doc.__dict__
            d["createdAt"] = datetime.datetime.now(tz=utc)
            d["modifiedAt"] = d["createdAt"]
            writer.add_document(uid=uid, **d)
        writer.commit()

    async def delete_batch(self, uid: str, nids: List[str]):
        writer = self.ix.writer()
        for nid in nids:
            q = And([Term("uid", uid), Term("nid", nid)])
            writer.delete_by_query(q=q)
        writer.commit()

    async def update_batch(self, uid: str, docs: List[SearchDoc]):
        writer = self.ix.writer()
        for doc in docs:
            with self.ix.searcher() as searcher:
                res = searcher.search(And([Term("uid", uid), Term("nid", doc.nid)]))
                if len(res) != 1:
                    raise ValueError(f"nid {doc.nid} not found or more than one found")
                res = res[0]
                new = {
                    "createdAt": res["createdAt"],
                    "nid": doc.nid,
                    "modifiedAt": datetime.datetime.now(tz=utc),
                    "title": doc.title if doc.title != "" else res["title"],
                    "md": doc.md if doc.md != "" else res["md"],
                }
                writer.delete_by_term("nid", doc.nid)
            writer.add_document(uid=uid, **new)
        writer.commit()

    async def search(
            self,
            uid: str,
            query: str,
            sort_key: str = None,
            reverse: bool = False,
            page: int = 1,
            page_size: int = 10,
    ) -> Tuple[List[SearchResult], int]:
        hits = []
        with self.ix.searcher() as searcher:
            qp = QueryParser("md", self.ix.schema)
            q = qp.parse(query)
            q = And([Term("uid", uid), q])
            results = searcher.search_page(
                q,
                pagenum=page,
                pagelen=page_size,
                sortedby=sort_key,
                reverse=reverse,
            )
            if (page - 1) * page_size > results.total:
                return hits, results.total
            hl = Highlighter(formatter=HtmlFormatter(
                tagname=self.hl_tag_name,
                classname=self.hl_class_name,
                termclass=self.hl_term_prefix
            )),
            results.highlighter = hl
            for hit in results:
                hits.append(
                    SearchResult(
                        nid=hit["nid"],
                        title=hit["title"],
                        md=hit["md"],
                        score=hit.score,
                        highlights=hit.highlights("md"),
                        modifiedAt=hit["modifiedAt"],
                        createdAt=hit["createdAt"],
                    )
                )
        return hits, results.total
