from pydantic import BaseModel, NonNegativeInt


class FileUploadResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    failedFilename: str
