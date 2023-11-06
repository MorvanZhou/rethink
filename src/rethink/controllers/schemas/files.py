from typing import List, Dict

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


class ImageUploadResponse(BaseModel):
    class Data(BaseModel):
        errFiles: List[str]
        succMap: Dict[str, str]

    code: NonNegativeInt
    msg: str
    data: Data
