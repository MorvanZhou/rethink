from typing import Literal

from pydantic import BaseModel, NonNegativeInt, EmailStr, Field

from rethink import const


class UserInfoResponse(BaseModel):
    class User(BaseModel):
        class LastState(BaseModel):
            nodeDisplayMethod: NonNegativeInt
            nodeDisplaySortKey: str

        class Settings(BaseModel):
            language: Literal["en", "zh"]
            theme: Literal["light", "dark"]
            editorMode: Literal["ir", "wysiwyg"]
            editorFontSize: NonNegativeInt
            editorCodeTheme: Literal["dracula", "github"]

        email: str
        nickname: str
        avatar: str
        createdAt: str
        usedSpace: NonNegativeInt = 0
        maxSpace: NonNegativeInt = 0
        lastState: LastState
        settings: Settings

    code: NonNegativeInt
    message: str
    requestId: str
    user: User = None


class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=const.EMAIL_MAX_LENGTH)
    password: str = Field(max_length=const.PASSWORD_MAX_LENGTH)
    captchaToken: str = Field(max_length=2000)
    captchaCode: str = Field(max_length=10)
    language: Literal["en", "zh"]
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=const.EMAIL_MAX_LENGTH)
    password: str = Field(max_length=const.PASSWORD_MAX_LENGTH)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class UpdateRequest(BaseModel):
    nickname: str = Field(default="", max_length=const.NICKNAME_MAX_LENGTH)
    avatar: str = Field(default="", max_length=2048)
    nodeDisplayMethod: int = Field(default=-1, ge=-1, le=10)
    nodeDisplaySortKey: Literal["modifiedAt", "createdAt", "title", ""] = Field(default="", max_length=20)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class EmailVerificationRequest(BaseModel):
    email: str = Field(max_length=const.EMAIL_MAX_LENGTH)
    captchaToken: str = Field(max_length=2000)
    captchaCode: str = Field(max_length=10)
    language: Literal["en", "zh"] = const.Language.EN.value
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class ResetPasswordRequest(BaseModel):
    email: str = Field(max_length=const.EMAIL_MAX_LENGTH)
    newPassword: str = Field(max_length=const.PASSWORD_MAX_LENGTH)
    verification: str = Field(max_length=const.PASSWORD_MAX_LENGTH)
    verificationToken: str = Field(max_length=2000)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class UpdateSettingsRequest(BaseModel):
    language: Literal["en", "zh"] = const.Language.EN.value
    theme: Literal["light", "dark", ""] = ""
    editorMode: Literal["ir", "wysiwyg", ""] = ""
    editorFontSize: int = -1
    editorCodeTheme: Literal["dracula", "github", ""] = ""
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)
