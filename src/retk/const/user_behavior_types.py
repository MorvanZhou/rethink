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
    NODE_RECOMMEND_KNOWLEDGE_VIEW = 13

    USER_REGISTERED = 14  # backend
    NODE_BROWSER_EXTENSION_CREATE = 15  # backend

    NODE_RECOMMEND_KNOWLEDGE_ACCEPT = 16  # backend
    NODE_RECOMMEND_KNOWLEDGE_REJECT = 17  # backend

    NODE_FAVORITE_ADD = 18  # backend
    NODE_FAVORITE_REMOVE = 19  # backend
    NODE_FAVORITE_VIEW = 20  # backend

    NODE_DATA_IMPORT = 21  # backend
    NODE_DATA_EXPORT = 22  # backend
    NODE_FILE_UPLOAD = 23  # backend

    LLM_KNOWLEDGE_RESPONSE = 24  # backend
    NODE_PAGE_VIEW = 25  # backend


USER_BEHAVIOR_TYPE_MAP = {
    t.value: t
    for t in UserBehaviorTypeEnum.__members__.values()
}
