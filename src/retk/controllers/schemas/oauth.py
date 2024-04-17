from pydantic import BaseModel, HttpUrl


class OAuthResponse(BaseModel):
    uri: HttpUrl
