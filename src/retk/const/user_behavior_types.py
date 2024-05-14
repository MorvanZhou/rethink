from enum import IntEnum, unique


@unique
class UserBehaviorTypeEnum(IntEnum):
    LOGIN = 0  # backend
    LOGOUT = 1  # backend
    # node ops, backend
    NODE_CREATE = 2
    NODE_QUICK_CREATE = 3
    NODE_TRASHED_OPS = 4
    NODE_RESTORED_OPS = 5
    NODE_DELETED_OPS = 6
    # search, backend
    SEARCH_GLOBAL = 7
    SEARCH_AT = 8
    # at ops, frontend
    AT_NODE = 9
    AT_RECOMMENDED_NODE = 10
    # view node, frontend
    VIEW_NODE_FROM_RECOMMENDATION = 11
    VIEW_NODE_FROM_LINKED_NODE = 12


USER_BEHAVIOR_TYPE_MAP = {
    t.value: t
    for t in UserBehaviorTypeEnum.__members__.values()
}
