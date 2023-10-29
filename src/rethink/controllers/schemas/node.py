from typing import List, Optional

from pydantic import BaseModel, NonNegativeInt, Field

from ..utils import datetime2str


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


class NodesInfoResponse(BaseModel):
    class Data(BaseModel):
        class NodeInfo(BaseModel):
            id: str
            title: str
            snippet: str
            type: int
            createdAt: str
            modifiedAt: str

        nodes: List[NodeInfo]
        total: NonNegativeInt

    code: NonNegativeInt
    message: str
    requestId: str
    data: Data


class RestoreFromTrashRequest(BaseModel):
    requestId: str
    nid: str


class GetFromTrashResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    data: NodesInfoResponse.Data


def parse_nodes_info(nodes, total):
    data = NodesInfoResponse.Data(
        nodes=[NodesInfoResponse.Data.NodeInfo(
            id=n["id"],
            title=n["title"],
            snippet=n["snippet"],
            type=n["type"],
            createdAt=datetime2str(n["_id"].generation_time),
            modifiedAt=datetime2str(n["modifiedAt"]),
        ) for n in nodes],
        total=total,
    )
    return data


class BatchNodeIdsRequest(BaseModel):
    requestId: str
    nids: List[str]
