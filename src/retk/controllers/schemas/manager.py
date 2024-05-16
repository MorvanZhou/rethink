from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from retk.const import settings, notice


class GetUserRequest(BaseModel):
    email: Optional[str] = Field(max_length=settings.EMAIL_MAX_LENGTH, default=None)
    uid: Optional[str] = Field(max_length=settings.UID_MAX_LENGTH, default=None)


class ManagerNoticeDeliveryRequest(BaseModel):
    title: str = Field(
        max_length=settings.MAX_SYSTEM_NOTICE_TITLE_LENGTH,
        description="title"
    )
    content: str = Field(
        max_length=settings.MAX_SYSTEM_NOTICE_CONTENT_LENGTH,
        description="content"
    )
    recipientType: notice.RecipientTypeEnum = Field(..., description="recipient type")
    batchTypeIds: List[str] = Field(
        default_factory=list,
        description="list of user ID if the recipientType is batch"
    )
    publishAt: datetime = Field(..., description="publish time")
