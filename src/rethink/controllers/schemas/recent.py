from typing import List

from pydantic import Field, BaseModel

from rethink import const


class AtNodeRequest(BaseModel):
    nid: str = Field(max_length=const.NID_MAX_LENGTH)
    toNid: str = Field(max_length=const.NID_MAX_LENGTH)


class GetRecentSearchResponse(BaseModel):
    requestId: str
    queries: List[str]
