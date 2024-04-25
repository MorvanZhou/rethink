from pydantic import BaseModel, Field

from retk.const import settings


class UidRequest(BaseModel):
    uid: str = Field(max_length=settings.UID_MAX_LENGTH)


class EmailRequest(BaseModel):
    email: str = Field(max_length=settings.EMAIL_MAX_LENGTH)
