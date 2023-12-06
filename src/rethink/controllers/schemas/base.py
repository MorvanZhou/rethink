from typing import Optional

from pydantic import BaseModel, NonNegativeInt


class AcknowledgeResponse(BaseModel):
    code: int
    message: str
    requestId: str


class TokenResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: Optional[str]
    token: str = ""
