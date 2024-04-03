import datetime
from typing import List, Optional, Dict, Literal

from bson import ObjectId
from typing_extensions import TypedDict

CODE_THEME_TYPES = Literal[
    "dracula", "github", "emacs", "tango", "",
]


# not used, just for reference
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
    uid: str
    md: str
    title: str
    snippet: str
    type: int  # const.NodeType.MARKDOWN.value
    disabled: bool
    inTrash: bool
    modifiedAt: datetime.datetime
    inTrashAt: Optional[datetime.datetime]
    fromNodeIds: List[str]
    toNodeIds: List[str]
    history: List[str]


class _LastState(TypedDict):
    nodeDisplayMethod: int
    nodeDisplaySortKey: str
    recentSearch: List[str]
    recentCursorSearchSelectedNIds: List[str]


class _Settings(TypedDict):
    language: str
    theme: Literal["light", "dark"]
    editorMode: Literal["ir", "wysiwyg"]
    editorFontSize: int
    editorCodeTheme: CODE_THEME_TYPES
    editorSepRightWidth: int
    editorSideCurrentToolId: str


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
    usedSpace: int
    type: int
    lastState: _LastState
    settings: _Settings


class UserFile(TypedDict):
    _id: ObjectId
    uid: str
    fid: str
    filename: str
    size: int


class ImportData(TypedDict):
    _id: ObjectId
    uid: str
    process: int
    type: str
    startAt: datetime.datetime
    running: bool
    msg: str
    code: int
    obsidian: Dict[str, str]  # filename: nid
