from enum import IntEnum


# 0: batch, 1: all, 2: admin, 3: manager
class RecipientTypeEnum(IntEnum):
    BATCH = 0
    ALL = 1
    ADMIN = 2
    MANAGER = 3
