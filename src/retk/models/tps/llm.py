from typing import TypedDict, List

from bson import ObjectId


class NodeExtendQueue(TypedDict):
    _id: ObjectId
    uid: str
    nid: str
    summaryService: str
    summaryModel: str
    extendService: str
    extendModel: str


class ExtendedNode(TypedDict):
    _id: ObjectId
    uid: str
    sourceNids: List[str]
    sourceMd: List[str]
    extendMd: str
