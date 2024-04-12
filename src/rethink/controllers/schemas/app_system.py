from typing import Tuple

from pydantic import Field, BaseModel, NonNegativeInt


class LatestVersionResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    version: Tuple[int, int, int] = Field(default=(0, 0, 0))
