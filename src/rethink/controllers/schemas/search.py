from typing import List, Sequence

from pydantic import Field, BaseModel, NonNegativeInt

from .node import NodesInfoResponse


class SearchUserNodesRequest(BaseModel):
    requestId: str
    query: str = ""
    sortKey: str = "createdAt"
    sortOrder: int = -1
    page: NonNegativeInt = 0
    pageSize: NonNegativeInt = 0
    nidExclude: Sequence[str] = Field(default_factory=list)


class CursorQueryRequest(BaseModel):
    nid: str
    textBeforeCursor: str
    requestId: str = ""


class CursorQueryResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    nodes: List[NodesInfoResponse.Data.NodeInfo]


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
