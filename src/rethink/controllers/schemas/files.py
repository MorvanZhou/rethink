from pydantic import BaseModel, NonNegativeInt


class FileUploadResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    failedFilename: str


class FileUploadProcessResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    process: int
    type: str
    startAt: str
    running: bool
