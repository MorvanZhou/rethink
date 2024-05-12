from typing import Optional

from pydantic import BaseModel, NonNegativeInt, Field, NonNegativeFloat

from retk.const import settings, LanguageEnum, app, NodeDisplaySortKeyEnum


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
    uid: str
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
