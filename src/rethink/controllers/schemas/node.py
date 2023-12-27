from typing import List, Optional

from pydantic import BaseModel, NonNegativeInt, Field

from rethink import const
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
    md: str = Field(max_length=const.MD_MAX_LENGTH)
    type: NonNegativeInt
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)
    fromNid: str = Field(default="", max_length=const.NID_MAX_LENGTH)


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
    nid: str = Field(max_length=const.NID_MAX_LENGTH)
    md: str = Field(max_length=const.MD_MAX_LENGTH)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class RestoreFromTrashRequest(BaseModel):
    nid: str = Field(max_length=const.NID_MAX_LENGTH)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class GetFromTrashResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    data: NodesSearchResponse.Data


class BatchNodeIdsRequest(BaseModel):
    nids: List[str] = Field(default_factory=list, min_items=1, max_items=1000)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)
