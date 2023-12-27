from typing import List, Sequence, Literal

from pydantic import Field, BaseModel, NonNegativeInt

from rethink import const


class NodesSearchResponse(BaseModel):
    class Data(BaseModel):
        class Node(BaseModel):
            id: str
            title: str
            snippet: str
            titleHighlight: str
            bodyHighlights: List[str]
            score: float
            type: int
            createdAt: str
            modifiedAt: str

        nodes: List[Node]
        total: NonNegativeInt

    code: NonNegativeInt
    message: str
    requestId: str
    data: Data


class SearchUserNodesRequest(BaseModel):
    query: str = Field(default="", max_length=const.SEARCH_QUERY_MAX_LENGTH)
    sortKey: Literal[
        "createdAt", "modifiedAt", "title", "similarity"
    ] = Field(default="createdAt", max_length=20)
    reverse: bool = False
    page: NonNegativeInt = 0
    pageSize: NonNegativeInt = 0
    nidExclude: Sequence[str] = Field(default_factory=list, max_items=1000)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class CursorQueryRequest(BaseModel):
    nid: str = Field(max_length=const.NID_MAX_LENGTH)
    query: str = Field(max_length=const.SEARCH_QUERY_MAX_LENGTH)
    page: NonNegativeInt = 0
    pageSize: NonNegativeInt = 0
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class RecommendNodesRequest(BaseModel):
    content: str = Field(max_length=const.RECOMMEND_CONTENT_MAX_LENGTH)
    nidExclude: Sequence[str] = Field(default_factory=list, max_items=1000)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class RecommendNodesResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    nodes: List[NodesSearchResponse.Data.Node]


class AddToRecentSearchHistRequest(BaseModel):
    nid: str = Field(max_length=const.NID_MAX_LENGTH)
    toNid: str = Field(max_length=const.NID_MAX_LENGTH)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class GetRecentSearchResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    queries: List[str]
