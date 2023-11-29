from typing import List, Sequence

from pydantic import Field, BaseModel, NonNegativeInt

from .node import NodesSearchResponse


class SearchUserNodesRequest(BaseModel):
    requestId: str
    query: str = ""
    sortKey: str = "createdAt"
    reverse: bool = False
    page: NonNegativeInt = 0
    pageSize: NonNegativeInt = 0
    nidExclude: Sequence[str] = Field(default_factory=list)


class CursorQueryRequest(BaseModel):
    nid: str
    textBeforeCursor: str
    page: NonNegativeInt = 0
    pageSize: NonNegativeInt = 0
    requestId: str = ""


class CursorQueryResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    nodes: List[NodesSearchResponse.Data.Node]


class AddToRecentSearchHistRequest(BaseModel):
    requestId: str
    nid: str
    toNid: str


class PutRecentSearchRequest(BaseModel):
    requestId: str
    query: str


class GetRecentSearchResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    queries: List[str]
