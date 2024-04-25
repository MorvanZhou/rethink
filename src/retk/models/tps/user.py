from datetime import datetime
from typing import List, Literal, TypedDict

from bson import ObjectId

CODE_THEME_TYPES = Literal[
    "dracula", "github", "emacs", "tango",
]


class _LastState(TypedDict):
    nodeDisplayMethod: int
    nodeDisplaySortKey: str
    recentSearch: List[str]
    recentCursorSearchSelectedNIds: List[str]  # at search


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
    modifiedAt: datetime
    usedSpace: int
    type: int
    lastState: _LastState
    settings: _Settings
