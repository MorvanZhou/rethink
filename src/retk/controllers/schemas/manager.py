from typing import Optional

from pydantic import BaseModel, Field

from retk.const import settings


class GetUserRequest(BaseModel):
    email: Optional[str] = Field(max_length=settings.EMAIL_MAX_LENGTH, default=None)
    uid: Optional[str] = Field(max_length=settings.UID_MAX_LENGTH, default=None)
