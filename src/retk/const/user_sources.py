from enum import IntEnum, unique


@unique
class UserSourceEnum(IntEnum):
    TEST = 0
    EMAIL = 1
    PHONE = 2
    GOOGLE = 3
    FACEBOOK = 4
    WECHAT = 5
    GITHUB = 6
    LOCAL = 7

    def __str__(self):
        return self.value
