from typing import List

from rethink.models.database import COLL


def delete_files(
        uid: str,
        files: List[str],
) -> List[str]:
    docs = COLL.user_file.find({"uid": uid, "filename": {"$in": files}})
    # TODO: delete file from usedSpace
    return list(files)
