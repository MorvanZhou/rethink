from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, NonNegativeInt, Field, NonNegativeFloat

from retk import config
from retk.const import settings, LanguageEnum, app, NodeDisplaySortKeyEnum, USER_TYPE
from retk.models import tps
from retk.utils import datetime2str


class UserInfoResponse(BaseModel):
    class User(BaseModel):
        class LastState(BaseModel):
            nodeDisplayMethod: NonNegativeInt
            nodeDisplaySortKey: NodeDisplaySortKeyEnum

        class Settings(BaseModel):
            language: LanguageEnum
            theme: app.AppThemeEnum
            editorMode: app.EditorModeEnum
            editorFontSize: NonNegativeInt
            editorCodeTheme: app.EditorCodeThemeEnum
            editorSepRightWidth: float
            editorSideCurrentToolId: str

        email: str
        nickname: str
        avatar: str
        source: int
        createdAt: str
        usedSpace: NonNegativeInt = 0
        maxSpace: NonNegativeInt = 0
        lastState: LastState
        settings: Settings

    requestId: str
    user: User = None


class PatchUserRequest(BaseModel):
    class LastState(BaseModel):
        nodeDisplayMethod: Optional[NonNegativeInt] = Field(default=None, ge=-1, le=10)
        nodeDisplaySortKey: Optional[NodeDisplaySortKeyEnum] = Field(
            default=None, max_length=20
        )

    class Settings(BaseModel):
        language: Optional[LanguageEnum] = Field(default=None)
        theme: Optional[app.AppThemeEnum] = Field(default=None)
        editorMode: Optional[app.EditorModeEnum] = Field(default=None)
        editorFontSize: Optional[NonNegativeInt] = Field(default=None)
        editorCodeTheme: Optional[app.EditorCodeThemeEnum] = Field(default=None)
        editorSepRightWidth: Optional[NonNegativeFloat] = Field(default=None)
        editorSideCurrentToolId: Optional[str] = Field(default=None)

    nickname: Optional[str] = Field(default=None, max_length=settings.NICKNAME_MAX_LENGTH)
    avatar: Optional[str] = Field(default=None, max_length=2048)
    lastState: Optional[LastState] = Field(default=None)
    settings: Optional[Settings] = Field(default=None)


class UpdatePasswordRequest(BaseModel):
    oldPassword: str = Field(max_length=settings.PASSWORD_MAX_LENGTH)
    newPassword: str = Field(max_length=settings.PASSWORD_MAX_LENGTH)


def get_user_info_response_from_u_dict(
        u: tps.UserMeta,
        request_id: str,
) -> UserInfoResponse:
    if config.is_local_db():
        max_space = 0
    else:
        max_space = USER_TYPE.id2config(u["type"]).max_store_space
    last_state = u["lastState"]
    u_settings = u["settings"]
    return UserInfoResponse(
        requestId=request_id,
        user=UserInfoResponse.User(
            email=u["email"],
            nickname=u["nickname"],
            avatar=u["avatar"],
            source=u["source"],
            createdAt=datetime2str(u["_id"].generation_time),
            usedSpace=u["usedSpace"],
            maxSpace=max_space,
            lastState=UserInfoResponse.User.LastState(
                nodeDisplayMethod=last_state["nodeDisplayMethod"],
                nodeDisplaySortKey=last_state["nodeDisplaySortKey"],
            ),
            settings=UserInfoResponse.User.Settings(
                language=u_settings["language"],
                theme=u_settings["theme"],
                editorMode=u_settings["editorMode"],
                editorFontSize=u_settings["editorFontSize"],
                editorCodeTheme=u_settings["editorCodeTheme"],
                editorSepRightWidth=u_settings.get("editorSepRightWidth", 200),
                editorSideCurrentToolId=u_settings.get("editorSideCurrentToolId", ""),
            ),
        ),
    )


class NotificationResponse(BaseModel):
    class System(BaseModel):
        class Notice(BaseModel):
            id: str
            title: str
            snippet: str
            publishAt: str
            read: bool
            readTime: Optional[datetime]

        total: int
        notices: List[Notice]

    requestId: str
    hasUnread: bool
    system: System
