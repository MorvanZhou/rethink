from typing import Any, Dict, Optional

from mongita.results import UpdateResult

from rethink import config
from .database import COLL
from .tps import Node


def remove_from_node(from_nid: str, to_nid: str):
    if config.is_local_db():
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


# def remove_to_node(from_nid: str, to_nid: str):
#     if config.is_local_db():
#         from_n = COLL.nodes.find_one({"id": from_nid})
#         if from_n is None:
#             return
#         try:
#             from_n["toNodeIds"].remove(to_nid)
#             COLL.nodes.update_one(
#                 {"id": from_nid},
#                 {"$set": {"toNodeIds": from_n["toNodeIds"]}}
#             )
#         except ValueError:
#             pass
#     else:
#         COLL.nodes.update_one(
#             {"id": from_nid},
#             {"$pull": {"toNodeIds": to_nid}}
#         )


def node_add_to_set(id_: str, key: str, value: Any) -> UpdateResult:
    res = UpdateResult(0, 0)
    if config.is_local_db():
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


def node_get(
        id_: str,
        assert_conditions: Dict[str, Any]
) -> Optional[Node]:
    c = {"id": id_}
    if not config.is_local_db():
        c.update(assert_conditions)

    doc = COLL.nodes.find_one(c)
    if doc is None:
        return None
    if config.is_local_db():
        for k, c in assert_conditions.items():
            if doc[k] != c:
                return None
    return doc


def unids_pull(id_: str, key: str, value: Any) -> UpdateResult:
    res = UpdateResult(0, 0)
    if config.is_local_db():
        doc = COLL.unids.find_one({"id": id_})
        if doc is None:
            return res
        if key not in doc:
            doc[key] = []
        if value in doc[key]:
            doc[key].remove(value)
            res = COLL.unids.update_one(
                {"id": id_},
                {"$set": {key: doc[key]}}
            )
    else:
        res = COLL.users.update_one(
            {"id": id_},
            {"$pull": {key: value}}
        )
    return res
