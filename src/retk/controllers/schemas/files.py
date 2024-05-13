from typing import List, Dict

from pydantic import BaseModel, NonNegativeInt


class FileUploadProcessResponse(BaseModel):
    requestId: str
    code: NonNegativeInt
    msg: str
    process: int
    type: str
    startAt: str
    running: bool


class VditorFilesResponse(BaseModel):
    class Data(BaseModel):
        errFiles: List[str]
        succMap: Dict[str, str]

    msg: str
    code: NonNegativeInt
    requestId: str
    data: Data


class ImageVditorFetchRequest(BaseModel):
    url: str


class VditorImagesResponse(BaseModel):
    class Data(BaseModel):
        originalURL: str
        url: str

    msg: str
    code: NonNegativeInt
    requestId: str
    data: Data
