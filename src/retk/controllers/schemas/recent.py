from typing import List

from pydantic import Field, BaseModel

from retk.const import settings


class AtNodeRequest(BaseModel):
    nid: str = Field(max_length=settings.NID_MAX_LENGTH)
    toNid: str = Field(max_length=settings.NID_MAX_LENGTH)


class GetRecentSearchResponse(BaseModel):
    requestId: str
    queries: List[str]
