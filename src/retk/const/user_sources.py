from enum import Enum, auto, unique


@unique
class UserSource(Enum):
    TEST = 0
    EMAIL = auto()  # 1
    PHONE = auto()  # 2
    GOOGLE = auto()  # 3
    FACEBOOK = auto()  # 4
    WECHAT = auto()  # 5
    GITHUB = auto()  # 6
    LOCAL = auto()  # 7

    def __str__(self):
        return self.value
