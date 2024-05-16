import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Sequence, Literal

from retk import const
from retk.models.tps import AuthedUser
from retk.utils import strip_html_tags


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
    async def close(self):
        ...

    @abstractmethod
    async def drop(self):
        ...

    @abstractmethod
    async def add(self, au: AuthedUser, doc: SearchDoc) -> const.CodeEnum:
        ...

    @abstractmethod
    async def update(self, au: AuthedUser, doc: SearchDoc) -> const.CodeEnum:
        ...

    @abstractmethod
    async def to_trash(self, au: AuthedUser, nid: str) -> const.CodeEnum:
        ...

    @abstractmethod
    async def restore_from_trash(self, au: AuthedUser, nid: str) -> const.CodeEnum:
        ...

    @abstractmethod
    async def disable(self, au: AuthedUser, nid: str) -> const.CodeEnum:
        ...

    @abstractmethod
    async def enable(self, au: AuthedUser, nid: str) -> const.CodeEnum:
        ...

    @abstractmethod
    async def delete(self, au: AuthedUser, nid: str) -> const.CodeEnum:
        ...

    @abstractmethod
    async def add_batch(self, au: AuthedUser, docs: List[SearchDoc]) -> const.CodeEnum:
        ...

    @abstractmethod
    async def delete_batch(self, au: AuthedUser, nids: List[str]) -> const.CodeEnum:
        ...

    @abstractmethod
    async def force_delete_all(self, uid: str) -> const.CodeEnum:
        ...

    @abstractmethod
    async def update_batch(self, au: AuthedUser, docs: List[SearchDoc]) -> const.CodeEnum:
        ...

    @abstractmethod
    async def batch_to_trash(self, au: AuthedUser, nids: List[str]) -> const.CodeEnum:
        ...

    @abstractmethod
    async def restore_batch_from_trash(self, au: AuthedUser, nids: List[str]) -> const.CodeEnum:
        ...

    @abstractmethod
    async def _search(
            self,
            au: AuthedUser,
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
            au: AuthedUser,
            query: str = "",
            sort_key: Literal[
                "createdAt", "modifiedAt", "title", "similarity"
            ] = None,
            reverse: bool = False,
            page: int = 1,
            limit: int = 10,
            exclude_nids: Sequence[str] = None,
    ) -> Tuple[List[SearchResult], int]:
        ...

    @abstractmethod
    async def recommend(
            self,
            au: AuthedUser,
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
    async def batch_restore_docs(self, au: AuthedUser, docs: List[RestoreSearchDoc]) -> const.CodeEnum:
        ...
