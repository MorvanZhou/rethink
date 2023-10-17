import datetime
from typing import List, Optional

from bson import ObjectId
from typing_extensions import TypedDict


class LinkedNode(TypedDict):
    _id: ObjectId
    id: str
    title: str
    text: str
    type: int  # const.NodeType.MARKDOWN.value
    disabled: bool
    modifiedAt: datetime.datetime


class Node(TypedDict):
    _id: ObjectId
    id: str
    title: str
    searchKeys: str
    text: str
    snippet: str
    type: int  # const.NodeType.MARKDOWN.value
    disabled: bool
    inTrash: bool
    modifiedAt: datetime.datetime
    inTrashAt: Optional[datetime.datetime]
    fromNodeIds: List[str]
    toNodeIds: List[str]
    fromNodes: Optional[List[LinkedNode]]
    toNodes: Optional[List[LinkedNode]]


class UserMeta(TypedDict):
    _id: ObjectId
    id: str
    source: int
    account: str
    nickname: str
    email: str
    avatar: str
    hashed: str
    disabled: bool
    modifiedAt: datetime.datetime
    recentSearchQueries: List[str]
    recentSearchedNodeIds: List[str]
    language: str


class UserNodeIds(TypedDict):
    _id: ObjectId
    id: str
    nodeIds: List[str]
