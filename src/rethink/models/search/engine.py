import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class SearchDoc:
    nid: str
    title: str
    md: str


@dataclass
class SearchResult:
    nid: str
    title: str
    md: str
    score: float
    highlights: str
    modifiedAt: datetime.datetime
    createdAt: datetime.datetime


class BaseEngine(ABC):
    hl_tag_name = "b"
    hl_class_name = "match"
    hl_term_prefix = "term"

    @abstractmethod
    async def init(self):
        ...

    @abstractmethod
    async def drop(self):
        ...

    @abstractmethod
    async def add(self, uid: str, doc: SearchDoc):
        ...

    @abstractmethod
    async def update(self, uid: str, doc: SearchDoc):
        ...

    @abstractmethod
    async def delete(self, uid: str, nid: str):
        ...

    @abstractmethod
    async def add_batch(self, uid: str, docs: List[SearchDoc]):
        ...

    @abstractmethod
    async def delete_batch(self, uid: str, nids: List[str]):
        ...

    @abstractmethod
    async def update_batch(self, uid: str, docs: List[SearchDoc]):
        ...

    @abstractmethod
    async def search(
            self,
            uid: str,
            query: str,
            sort_key: str = None,
            reverse: bool = False,
            page: int = 1,
            page_size: int = 10,
    ) -> Tuple[List[SearchResult], int]:
        ...
