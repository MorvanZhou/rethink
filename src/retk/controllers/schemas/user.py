from typing import Literal, Optional

from pydantic import BaseModel, NonNegativeInt, Field, NonNegativeFloat
from retk import const
from retk.models.tps import CODE_THEME_TYPES


class UserInfoResponse(BaseModel):
    class User(BaseModel):
        class LastState(BaseModel):
            nodeDisplayMethod: NonNegativeInt
            nodeDisplaySortKey: Literal["modifiedAt", "createdAt", "title", "similarity"]

        class Settings(BaseModel):
            language: Literal["en", "zh"]
            theme: Literal["light", "dark"]
            editorMode: Literal["ir", "wysiwyg"]
            editorFontSize: NonNegativeInt
            editorCodeTheme: CODE_THEME_TYPES
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
        nodeDisplaySortKey: Optional[Literal["modifiedAt", "createdAt", "title"]] = Field(
            default=None, max_length=20
        )

    class Settings(BaseModel):
        language: Optional[Literal["en", "zh"]] = Field(default=None)
        theme: Optional[Literal["light", "dark"]] = Field(default=None)
        editorMode: Optional[Literal["ir", "wysiwyg"]] = Field(default=None)
        editorFontSize: Optional[NonNegativeInt] = Field(default=None)
        editorCodeTheme: Optional[CODE_THEME_TYPES] = Field(default=None)
        editorSepRightWidth: Optional[NonNegativeFloat] = Field(default=None)
        editorSideCurrentToolId: Optional[str] = Field(default=None)

    nickname: Optional[str] = Field(default=None, max_length=const.NICKNAME_MAX_LENGTH)
    avatar: Optional[str] = Field(default=None, max_length=2048)
    lastState: Optional[LastState] = Field(default=None)
    settings: Optional[Settings] = Field(default=None)


class UpdatePasswordRequest(BaseModel):
    oldPassword: str = Field(max_length=const.PASSWORD_MAX_LENGTH)
    newPassword: str = Field(max_length=const.PASSWORD_MAX_LENGTH)


class NotificationResponse(BaseModel):
    class Notification(BaseModel):
        id: str
        type: Literal["info", "warning", "error"]
        message: str
        createdAt: str

    requestId: str
    notifications: list[Notification]
