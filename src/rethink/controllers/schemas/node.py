from typing import List, Optional

from pydantic import BaseModel, NonNegativeInt, Field

from .search import NodesSearchResponse


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


class PutRequest(BaseModel):
    md: str
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
    md: str
    requestId: str = ""


class RestoreFromTrashRequest(BaseModel):
    requestId: str
    nid: str


class GetFromTrashResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    data: NodesSearchResponse.Data


class BatchNodeIdsRequest(BaseModel):
    requestId: str
    nids: List[str]
