from pydantic import BaseModel


class SystemNoticeResponse(BaseModel):
    class Notice(BaseModel):
        id: str
        title: str
        html: str
        publishAt: str

    requestId: str
    notice: Notice
