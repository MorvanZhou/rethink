from typing import TypedDict

from bson import ObjectId


class UserFile(TypedDict):
    _id: ObjectId
    uid: str
    fid: str
    filename: str
    size: int
