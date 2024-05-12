from enum import IntEnum, Enum, auto, unique


@unique
class NodeDisplayMethodEnum(IntEnum):
    CARD = 0
    LIST = auto()  # 1


@unique
class NodeDisplaySortKeyEnum(str, Enum):
    MODIFIED_AT = "modifiedAt"
    CREATED_AT = "createdAt"
    TITLE = "title"
    SIMILARITY = "similarity"
