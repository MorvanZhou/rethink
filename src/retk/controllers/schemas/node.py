from typing import List

from pydantic import BaseModel, NonNegativeInt, Field

from retk.const import settings


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
    md: str = Field(max_length=settings.MD_MAX_LENGTH)
    type: NonNegativeInt
    fromNid: str = Field(default="", max_length=settings.NID_MAX_LENGTH)


class NodeResponse(BaseModel):
    requestId: str
    node: NodeData


class PatchMdRequest(BaseModel):
    md: str = Field(max_length=settings.MD_MAX_LENGTH)


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

    requestId: str
    data: Data


class BatchNodeIdsRequest(BaseModel):
    nids: List[str] = Field(default_factory=list, min_length=1, max_length=1000)


class HistEditionsResponse(BaseModel):
    requestId: str
    versions: List[str] = Field(default_factory=list)


class HistEditionMdResponse(BaseModel):
    requestId: str
    md: str
