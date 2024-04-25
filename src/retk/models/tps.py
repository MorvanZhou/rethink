import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Literal

from bson import ObjectId
from typing_extensions import TypedDict

CODE_THEME_TYPES = Literal[
    "dracula", "github", "emacs", "tango",
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


class SystemNotice(TypedDict):
    _id: ObjectId
    adminId: str
    title: str
    content: str
    userType: int  # send to which user type, 0: all, 1: batch, 2: admin
    delivered: bool  # has been sent to user


@dataclass
class AuthedUser:
    __slots__ = ("u", "language", "request_id")

    @dataclass
    class User:
        __slots__ = (
            "_id", "id", "source", "account", "nickname", "email", "avatar", "hashed", "disabled",
            "modified_at", "used_space", "type", "last_state", "settings"
        )

        @dataclass
        class LastState:
            __slots__ = (
                "node_display_method", "node_display_sort_key",
                "recent_search", "recent_cursor_search_selected_nids"
            )
            node_display_method: int
            node_display_sort_key: str
            recent_search: List[str]
            recent_cursor_search_selected_nids: List[str]

        @dataclass
        class Settings:
            __slots__ = (
                "language", "theme", "editor_mode", "editor_font_size",
                "editor_code_theme", "editor_sep_right_width", "editor_side_current_tool_id"
            )
            language: str
            theme: str
            editor_mode: str
            editor_font_size: int
            editor_code_theme: str
            editor_sep_right_width: int
            editor_side_current_tool_id: str

        _id: ObjectId
        id: str
        source: int
        account: str
        nickname: str
        email: str
        avatar: str
        hashed: str
        disabled: bool
        modified_at: datetime.datetime
        used_space: int
        type: int
        last_state: LastState
        settings: Settings

    u: Optional[User]
    language: str
    request_id: str


def convert_user_dict_to_authed_user(u: UserMeta) -> AuthedUser.User:
    return AuthedUser.User(
        _id=u["_id"],
        id=u["id"],
        source=u["source"],
        account=u["account"],
        nickname=u["nickname"],
        email=u["email"],
        avatar=u["avatar"],
        hashed=u["hashed"],
        disabled=u["disabled"],
        modified_at=u["modifiedAt"],
        used_space=u["usedSpace"],
        type=u["type"],
        last_state=AuthedUser.User.LastState(
            node_display_method=u["lastState"]["nodeDisplayMethod"],
            node_display_sort_key=u["lastState"]["nodeDisplaySortKey"],
            recent_search=u["lastState"]["recentSearch"],
            recent_cursor_search_selected_nids=u["lastState"]["recentCursorSearchSelectedNIds"],
        ),
        settings=AuthedUser.User.Settings(
            language=u["settings"]["language"],
            theme=u["settings"]["theme"],
            editor_mode=u["settings"]["editorMode"],
            editor_font_size=u["settings"]["editorFontSize"],
            editor_code_theme=u["settings"]["editorCodeTheme"],
            editor_sep_right_width=u["settings"].get("editorSepRightWidth", 200),
            editor_side_current_tool_id=u["settings"].get("editorSideCurrentToolId", ""),
        ),
    )
