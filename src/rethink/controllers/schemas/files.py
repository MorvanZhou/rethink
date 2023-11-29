from typing import List, Dict

from pydantic import BaseModel, NonNegativeInt


class FileUploadResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str


class FileUploadProcessResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    process: int
    type: str
    startAt: str
    running: bool
    msg: str


class ImageVditorUploadResponse(BaseModel):
    class Data(BaseModel):
        errFiles: List[str]
        succMap: Dict[str, str]

    code: NonNegativeInt
    msg: str
    data: Data


class ImageVditorFetchRequest(BaseModel):
    url: str


class ImageVditorFetchResponse(BaseModel):
    class Data(BaseModel):
        originalURL: str
        url: str

    code: NonNegativeInt
    msg: str
    data: Data
