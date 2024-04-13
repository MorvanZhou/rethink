from typing import List, Dict

from pydantic import BaseModel, NonNegativeInt


class FileUploadProcessResponse(BaseModel):
    requestId: str
    process: int
    type: str
    startAt: str
    running: bool
    msg: str


class VditorFilesResponse(BaseModel):
    class Data(BaseModel):
        errFiles: List[str]
        succMap: Dict[str, str]

    code: NonNegativeInt
    msg: str
    requestId: str
    data: Data


class ImageVditorFetchRequest(BaseModel):
    url: str


class VditorImagesResponse(BaseModel):
    class Data(BaseModel):
        originalURL: str
        url: str

    requestId: str
    data: Data
