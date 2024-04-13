from typing import List

from pydantic import Field, BaseModel

from rethink import const


class AddToRecentSearchHistRequest(BaseModel):
    nid: str = Field(max_length=const.NID_MAX_LENGTH)
    toNid: str = Field(max_length=const.NID_MAX_LENGTH)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class GetRecentSearchResponse(BaseModel):
    requestId: str
    queries: List[str]
