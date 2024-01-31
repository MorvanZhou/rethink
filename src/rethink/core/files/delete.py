from typing import List

from rethink.models.client import client


def delete_files(
        uid: str,
        files: List[str],
) -> List[str]:
    docs = client.coll.user_file.find({"uid": uid, "filename": {"$in": files}})
    # TODO: delete file from usedSpace
    return list(files)
