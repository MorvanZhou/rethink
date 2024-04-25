from datetime import datetime
from typing import List, Optional, TypedDict

from bson import ObjectId


# not used, just for reference
class LinkedNode(TypedDict):
    _id: ObjectId
    id: str
    md: str
    title: str
    type: int  # const.NodeType.MARKDOWN.value
    disabled: bool
    modifiedAt: datetime


class Node(TypedDict):
    _id: ObjectId
    id: str
    uid: str
    md: str
    title: str
    snippet: str
    type: int  # const.NodeType.MARKDOWN.value
    disabled: bool
    inTrash: bool
    modifiedAt: datetime
    inTrashAt: Optional[datetime]
    fromNodeIds: List[str]
    toNodeIds: List[str]
    history: List[str]
