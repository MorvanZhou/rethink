from typing import TypedDict

from bson import ObjectId


class NodeExtendQueue(TypedDict):
    _id: ObjectId
    uid: str
    nid: str
    modifiedAt: int
    summaryService: str
    summaryModel: str
    extendService: str
    extendModel: str


class ExtendedNode(TypedDict):
    _id: ObjectId
    uid: str
    sourceNid: str
    sourceMd: str
    extendMd: str
