from typing import List, Optional

from pydantic import BaseModel, NonNegativeInt, Field

from rethink import const


class NodeData(BaseModel):
    class LinkedNode(BaseModel):
        id: str
        title: str
        md: str
        snippet: str
        type: NonNegativeInt
        disabled: bool
        inTrash: bool
        createdAt: str
        modifiedAt: str

    id: str
    md: str
    title: str
    snippet: str
    type: NonNegativeInt
    disabled: bool
    createdAt: str
    modifiedAt: str
    fromNodes: List[LinkedNode] = Field(default_factory=list)
    toNodes: List[LinkedNode] = Field(default_factory=list)


class CreateRequest(BaseModel):
    md: str = Field(max_length=const.MD_MAX_LENGTH)
    type: NonNegativeInt
    fromNid: str = Field(default="", max_length=const.NID_MAX_LENGTH)


class CreateResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    node: Optional[NodeData]


class GetResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    node: Optional[NodeData]


class PatchMdRequest(BaseModel):
    md: str = Field(max_length=const.MD_MAX_LENGTH)


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


class GetFromTrashResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    data: NodesSearchResponse.Data


class BatchNodeIdsRequest(BaseModel):
    nids: List[str] = Field(default_factory=list, min_length=1, max_length=1000)


class CoreNodesResponse(BaseModel):
    code: NonNegativeInt
    message: str
    data: NodesSearchResponse.Data
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class HistEditionsResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    versions: List[str] = Field(default_factory=list)


class HistEditionMdResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    md: str


class RecommendNodesResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    nodes: List[NodesSearchResponse.Data.Node] = Field(default_factory=list)
