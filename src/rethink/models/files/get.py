from typing import List, Tuple, Literal

from rethink.models.database import COLL
from rethink.models.tps import UserFile


def get_files(
        uid: str,
        page: int,
        page_size: int,
        sort: Literal["filename", "created_at", "size"] = "created_at",
) -> Tuple[List[UserFile], int]:
    docs = COLL.user_file.find({"uid": uid})
    total = docs.count()
    if sort == "filename":
        docs = docs.sort([("filename", 1), ("_id", -1)])
    elif sort == "created_at":
        docs = docs.sort("_id", direction=-1)
    elif sort == "size":
        docs = docs.sort([("size", -1), ("_id", -1)])

    docs = docs.skip((page - 1) * page_size).limit(page_size)
    return list(docs), total
