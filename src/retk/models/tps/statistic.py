from typing import TypedDict

from bson import ObjectId


class UserBehavior(TypedDict):
    _id: ObjectId
    uid: str
    type: int
    remark: str
