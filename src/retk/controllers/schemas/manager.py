from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from retk.const import settings, notice


class GetUserRequest(BaseModel):
    email: Optional[str] = Field(max_length=settings.EMAIL_MAX_LENGTH, default=None)
    github: Optional[str] = Field(max_length=50, default=None)
    uid: Optional[str] = Field(max_length=settings.UID_MAX_LENGTH, default=None)


class GetManagerDataResponse(BaseModel):
    class Data(BaseModel):
        userCount: int = Field(description="total number of users")
        nodeCount: int = Field(description="total number of nodes")

    requestId: str = Field(max_length=settings.REQUEST_ID_MAX_LENGTH, description="request ID")
    data: Data = Field(description="app data")


class GetUserResponse(BaseModel):
    class User(BaseModel):
        class LastState(BaseModel):
            nodeDisplayMethod: int
            nodeDisplaySortKey: str
            recentSearch: List[str]
            recentCursorSearchSelectedNIds: List[str]

        class Settings(BaseModel):
            language: str
            theme: str
            editorMode: str
            editorFontSize: int
            editorCodeTheme: str
            editorSepRightWidth: int
            editorSideCurrentToolId: str

        id: str
        source: int
        account: str
        nickname: str
        email: str
        avatar: str
        disabled: bool
        createdAt: str
        modifiedAt: str
        usedSpace: int
        type: int
        lastState: LastState
        settings: Settings

    requestId: str = Field(max_length=settings.REQUEST_ID_MAX_LENGTH, description="request ID")
    user: User = Field(description="user info")


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
        html: str = Field(description="html")
        snippet: str = Field(description="snippet")
        recipientType: notice.RecipientTypeEnum = Field(description="recipient type")
        batchTypeIds: List[str] = Field(description="list of user ID if the recipientType is batch")
        publishAt: datetime = Field(description="publish time")
        scheduled: bool = Field(description="scheduled")

    requestId: str = Field(max_length=settings.REQUEST_ID_MAX_LENGTH, description="request ID")
    notices: List[Notice] = Field(
        description="list of notices"
    )
    total: int = Field(description="total number of notices")
