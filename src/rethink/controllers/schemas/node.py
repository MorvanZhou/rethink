from typing import List, Optional

from pydantic import BaseModel, NonNegativeInt, Field


class NodeData(BaseModel):
    class LinkedNode(BaseModel):
        id: str
        title: str
        text: str
        snippet: str
        type: NonNegativeInt
        disabled: bool
        createdAt: str
        modifiedAt: str

    id: str
    title: str
    text: str
    type: NonNegativeInt
    disabled: bool
    createdAt: str
    modifiedAt: str
    fromNodes: List[LinkedNode] = Field(default_factory=list)
    toNodes: List[LinkedNode] = Field(default_factory=list)


class PutRequest(BaseModel):
    fulltext: str
    type: NonNegativeInt
    requestId: str = ""
    fromNid: str = ""


class PutResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    node: Optional[NodeData]


class GetResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    node: Optional[NodeData]


class UpdateRequest(BaseModel):
    nid: str
    fulltext: str
    requestId: str = ""


class NodesInfoResponse(BaseModel):
    class NodeInfo(BaseModel):
        id: str
        title: str
        snippet: str
        type: int
        createdAt: str
        modifiedAt: str

    code: NonNegativeInt
    message: str
    requestId: str
    nodes: List[NodeInfo]


class RestoreFromTrashRequest(BaseModel):
    requestId: str
    nid: str


class GetFromBinRequest(BaseModel):
    requestId: str
    page: NonNegativeInt = 0
    pageSize: NonNegativeInt = 0


class GetFromTrashResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    nodes: List[NodesInfoResponse.NodeInfo]
