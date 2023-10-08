from pydantic import BaseModel


class AcknowledgeResponse(BaseModel):
    code: int
    message: str
    requestId: str
