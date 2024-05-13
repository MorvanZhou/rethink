from datetime import datetime
from typing import List

from pydantic import BaseModel, NonNegativeInt, Field

from retk import const


class ManagerNoticeDeliveryRequest(BaseModel):
    senderId: str = Field(..., description="发送者 ID")
    title: str = Field(
        max_length=const.settings.MAX_SYSTEM_NOTICE_TITLE_LENGTH,
        description="title"
    )
    content: str = Field(
        max_length=const.settings.MAX_SYSTEM_NOTICE_CONTENT_LENGTH,
        description="content"
    )
    recipientType: NonNegativeInt = Field(..., description="recipient type")
    batchTypeIds: List[str] = Field(
        default_factory=list,
        description="list of user ID if the recipientType is batch"
    )
    publishAt: datetime = Field(..., description="发布时间")


class NotificationResponse(BaseModel):
    class Data(BaseModel):
        class System(BaseModel):
            id: str
            title: str
            content: str
            publishAt: datetime
            read: bool
            readTime: datetime

        system: List[System]

    requestId: str
    data: Data
