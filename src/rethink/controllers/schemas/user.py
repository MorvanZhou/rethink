from typing import Optional, Literal

from pydantic import BaseModel, NonNegativeInt, HttpUrl, EmailStr, AfterValidator
from typing_extensions import Annotated


def empty_str_to_http_url(v: str) -> HttpUrl:
    if v == "":
        return v
    return HttpUrl(v)


class UserInfoResponse(BaseModel):
    class User(BaseModel):
        class LastState(BaseModel):
            nodeDisplayMethod: NonNegativeInt
            nodeDisplaySortKey: str

        email: str
        nickname: str
        avatar: Annotated[str, AfterValidator(empty_str_to_http_url)]
        createdAt: str
        language: Literal["en", "zh"]
        usedSpace: NonNegativeInt = 0
        maxSpace: NonNegativeInt = 0
        lastState: LastState

    code: NonNegativeInt
    message: str
    requestId: str
    user: User = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    language: Literal["en", "zh"]
    requestId: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    requestId: str = ""


class LoginResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: Optional[str]
    token: str = ""


class UpdateRequest(BaseModel):
    email: str = ""
    nickname: str = ""
    avatar: str = ""
    language: Literal["en", "zh"] = ""
    nodeDisplayMethod: int = -1
    nodeDisplaySortKey: str = ""
    requestId: str = ""
