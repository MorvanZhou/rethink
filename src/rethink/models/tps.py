import datetime
from typing import List, Optional

from bson import ObjectId
from typing_extensions import TypedDict


class LinkedNode(TypedDict):
    _id: ObjectId
    id: str
    md: str
    title: str
    type: int  # const.NodeType.MARKDOWN.value
    disabled: bool
    modifiedAt: datetime.datetime


class Node(TypedDict):
    _id: ObjectId
    id: str
    md: str
    title: str
    snippet: str
    type: int  # const.NodeType.MARKDOWN.value
    searchKeys: str
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
    recentSearch: List[str]
    recentCursorSearchSelectedNIds: List[str]
    language: str


class UserNodeIds(TypedDict):
    _id: ObjectId
    id: str
    nodeIds: List[str]
