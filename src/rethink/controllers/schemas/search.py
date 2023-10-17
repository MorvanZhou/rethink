from typing import List, Optional, Sequence

from pydantic import Field, BaseModel, NonNegativeInt

from .node import NodesInfoResponse


class SearchUserNodesRequest(BaseModel):
    requestId: str
    query: str = ""
    sortKey: str = "createAt"
    sortOrder: int = -1
    page: NonNegativeInt = 0
    pageSize: NonNegativeInt = 0
    nidExclude: Sequence[str] = Field(default_factory=list)


class CursorQueryRequest(BaseModel):
    nid: str
    textBeforeCursor: str
    requestId: str = ""


class CursorQueryResponse(BaseModel):
    class Result(BaseModel):
        nodes: List[NodesInfoResponse.Data.NodeInfo]
        query: Optional[str]

    code: NonNegativeInt
    message: str
    requestId: str
    result: Optional[Result]


class AddToRecentSearchHistRequest(BaseModel):
    requestId: str
    nid: str
    toNid: str


class RecentSearchQueriesResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    queries: List[str]
