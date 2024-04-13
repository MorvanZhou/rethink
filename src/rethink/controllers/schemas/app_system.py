from typing import Tuple

from pydantic import Field, BaseModel


class LatestVersionResponse(BaseModel):
    requestId: str
    version: Tuple[int, int, int] = Field(default=(0, 0, 0))
