from pydantic import BaseModel, Field

from retk import const


class UidRequest(BaseModel):
    uid: str = Field(max_length=const.UID_MAX_LENGTH)


class EmailRequest(BaseModel):
    email: str = Field(max_length=const.EMAIL_MAX_LENGTH)
