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


class GetSystemNoticesResponse(BaseModel):
    class Notice(BaseModel):
        id: str = Field(description="notice ID")
        title: str = Field(description="title")
        content: str = Field(description="content")
        recipientType: notice.RecipientTypeEnum = Field(description="recipient type")
        batchTypeIds: List[str] = Field(description="list of user ID if the recipientType is batch")
        publishAt: datetime = Field(description="publish time")
        scheduled: bool = Field(description="scheduled")

    requestId: str = Field(max_length=settings.REQUEST_ID_MAX_LENGTH, description="request ID")
    notices: List[Notice] = Field(
        description="list of notices"
    )
    total: int = Field(description="total number of notices")
