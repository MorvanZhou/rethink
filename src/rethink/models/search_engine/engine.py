import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Sequence, Literal

from rethink import const
from rethink.models.utils import strip_html_tags


@dataclass
class SearchDoc:
    nid: str
    title: str
    body: str

    def __post_init__(self):
        self.title = strip_html_tags(self.title)
        self.body = strip_html_tags(self.body)


@dataclass
class RestoreSearchDoc:
    nid: str
    title: str
    body: str
    createdAt: datetime.datetime
    modifiedAt: datetime.datetime
    disabled: bool
    inTrash: bool

    def __post_init__(self):
        self.title = strip_html_tags(self.title)
        self.body = strip_html_tags(self.body)


@dataclass
class SearchResult:
    nid: str
    score: float
    titleHighlight: str
    bodyHighlights: List[str]


STOPWORDS = sorted(list(set(
    (Path(__file__).parent / "cn_stopwords.txt").read_text(encoding="utf-8").splitlines()
    + (Path(__file__).parent / "baidu_stopwords.txt").read_text(encoding="utf-8").splitlines()
)))


class BaseEngine(ABC):
    hl_tag_name = "em"
    hl_class_name = "match"
    hl_term_prefix = "term"

    @abstractmethod
    async def init(self):
        ...

    @abstractmethod
    async def drop(self):
        ...

    @abstractmethod
    async def add(self, uid: str, doc: SearchDoc) -> const.Code:
        ...

    @abstractmethod
    async def update(self, uid: str, doc: SearchDoc) -> const.Code:
        ...

    @abstractmethod
    async def to_trash(self, uid: str, nid: str) -> const.Code:
        ...

    @abstractmethod
    async def restore_from_trash(self, uid: str, nid: str) -> const.Code:
        ...

    @abstractmethod
    async def disable(self, uid: str, nid: str) -> const.Code:
        ...

    @abstractmethod
    async def enable(self, uid: str, nid: str) -> const.Code:
        ...

    @abstractmethod
    async def delete(self, uid: str, nid: str) -> const.Code:
        ...

    @abstractmethod
    async def add_batch(self, uid: str, docs: List[SearchDoc]) -> const.Code:
        ...

    @abstractmethod
    async def delete_batch(self, uid: str, nids: List[str]) -> const.Code:
        ...

    @abstractmethod
    async def update_batch(self, uid: str, docs: List[SearchDoc]) -> const.Code:
        ...

    @abstractmethod
    async def batch_to_trash(self, uid: str, nids: List[str]) -> const.Code:
        ...

    @abstractmethod
    async def restore_batch_from_trash(self, uid: str, nids: List[str]) -> const.Code:
        ...

    @abstractmethod
    async def _search(
            self,
            uid: str,
            query: str = "",
            sort_key: str = None,
            reverse: bool = False,
            page: int = 1,
            page_size: int = 10,
            exclude_nids: Sequence[str] = None,
            with_stop_analyzer: bool = False,
    ):
        ...

    @abstractmethod
    async def search(
            self,
            uid: str,
            query: str = "",
            sort_key: Literal[
                "createdAt", "modifiedAt", "title", "similarity"
            ] = None,
            reverse: bool = False,
            page: int = 1,
            page_size: int = 10,
            exclude_nids: Sequence[str] = None,
    ) -> Tuple[List[SearchResult], int]:
        ...

    @abstractmethod
    async def recommend(
            self,
            uid: str,
            content: str,
            max_return: int = 10,
            exclude_nids: Sequence[str] = None,
    ) -> List[SearchResult]:
        ...

    @abstractmethod
    async def refresh(self):
        ...

    @abstractmethod
    async def count_all(self) -> int:
        ...

    @abstractmethod
    async def batch_restore_docs(self, uid: str, docs: List[RestoreSearchDoc]) -> const.Code:
        ...
