from datetime import datetime
from typing import Dict, TypedDict

from bson import ObjectId


class ImportData(TypedDict):
    _id: ObjectId
    uid: str
    process: int
    type: str
    startAt: datetime
    running: bool
    msg: str
    code: int
    obsidian: Dict[str, str]  # filename: nid
