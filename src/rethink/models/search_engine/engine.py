import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Sequence

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
    async def search(
            self,
            uid: str,
            query: str = "",
            sort_key: str = None,
            reverse: bool = False,
            page: int = 1,
            page_size: int = 10,
            exclude_nids: Sequence[str] = None,
    ) -> Tuple[List[SearchResult], int]:
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
