from pydantic import BaseModel, Field, HttpUrl

from retk.const import settings


class LoginTokenResponse(BaseModel):
    requestId: str
    accessToken: str
    refreshToken: str
    nickname: str
    uid: str


class RefreshTokenRequest(BaseModel):
    refreshToken: str = Field(max_length=2000)


class CreateNodeRequest(BaseModel):
    url: HttpUrl
    title: str = Field(max_length=200)
    content: str = Field(max_length=settings.MD_MAX_LENGTH)
