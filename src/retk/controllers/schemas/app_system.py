from pydantic import BaseModel


class AppUpdateResponse(BaseModel):
    requestId: str
    hasNewVersion: bool
    updated: bool
    message: str = ""
