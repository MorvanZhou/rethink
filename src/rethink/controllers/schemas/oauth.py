from pydantic import BaseModel, NonNegativeInt, HttpUrl


class OAuthResponse(BaseModel):
    code: NonNegativeInt
    message: str
    uri: HttpUrl
