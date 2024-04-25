from typing import TypedDict

from bson import ObjectId


class UserBehavior(TypedDict):
    _id: ObjectId
    uid: str
    bType: int
    remark: str
