from typing import Any, Dict, List

from mongita.results import UpdateResult

from rethink import config
from .database import COLL
from .tps import Node


def remove_from_node(from_nid: str, to_nid: str):
    if config.is_local_db():
        # no $pull support
        to_n = COLL.nodes.find_one({"id": to_nid})
        if to_n is None:
            return
        try:
            to_n["fromNodeIds"].remove(from_nid)
            COLL.nodes.update_one(
                {"id": to_nid},
                {"$set": {"fromNodeIds": to_n["fromNodeIds"]}}
            )
        except ValueError:
            pass
    else:
        COLL.nodes.update_one(
            {"id": to_nid},
            {"$pull": {"fromNodeIds": from_nid}}
        )


def node_add_to_set(id_: str, key: str, value: Any) -> UpdateResult:
    res = UpdateResult(0, 0)
    if config.is_local_db():
        # no $addToSet support
        has_new = False
        doc = COLL.nodes.find_one({"id": id_})
        if doc is None:
            return res
        if key not in doc:
            doc[key] = []
        if value not in doc[key]:
            doc[key].append(value)
            has_new = True
        if has_new:
            res = COLL.nodes.update_one(
                {"id": id_},
                {"$set": {key: doc[key]}}
            )
    else:
        res = COLL.nodes.update_one(
            {"id": id_},
            {"$addToSet": {key: value}}
        )
    return res


def nodes_get(
        uid: str,
        ids: List[str],
        assert_conditions: Dict[str, Any]
) -> List[Node]:
    c = {"id": {"$in": ids}, "uid": uid, **assert_conditions}
    docs = list(COLL.nodes.find(c))
    return docs
