from dataclasses import dataclass
from enum import Enum, auto, unique
from pathlib import Path
from textwrap import dedent

RETHINK_DIR = Path(__file__).parent
FRONTEND_DIR = RETHINK_DIR / "dist-local"
MD_MAX_LENGTH = 100000


class NodeType(Enum):
    FILE = 0
    MARKDOWN = auto()


class Code(Enum):
    OK = 0
    ACCOUNT_OR_PASSWORD_ERROR = auto()  # 1
    INVALID_AUTH = auto()  # 2
    EXPIRED_AUTH = auto()  # 3
    USER_EXIST = auto()  # 4
    NODE_EXIST = auto()  # 5
    NODE_NOT_EXIST = auto()  # 6
    OPERATION_FAILED = auto()  # 7
    EMAIL_OCCUPIED = auto()  # 8
    EMPTY_CONTENT = auto()  # 10
    INVALID_TITLE = auto()  # 11
    INVALID_LANGUAGE = auto()  # 12
    ONE_USER_MODE = auto()  # 13
    INVALID_PASSWORD = auto()  # 14
    CAPTCHA_ERROR = auto()  # 15
    CAPTCHA_EXPIRED = auto()  # 16
    NOTE_EXCEED_MAX_LENGTH = auto()  # 17


@dataclass
class CodeMessage:
    zh: str
    en: str


CODE_MESSAGES = {
    Code.OK: CodeMessage(zh="成功", en="OK"),
    Code.ACCOUNT_OR_PASSWORD_ERROR: CodeMessage(zh="账号不存在或者密码错误", en="No such user or password error"),
    Code.INVALID_AUTH: CodeMessage(zh="无效的认证信息", en="Invalid authentication information"),
    Code.EXPIRED_AUTH: CodeMessage(zh="认证信息已过期", en="Authentication information has expired"),
    Code.USER_EXIST: CodeMessage(zh="用户已存在", en="User already exists"),
    Code.NODE_EXIST: CodeMessage(zh="节点已存在", en="Node already exists"),
    Code.NODE_NOT_EXIST: CodeMessage(zh="节点不存在", en="Node does not exist"),
    Code.OPERATION_FAILED: CodeMessage(zh="操作失败", en="Operation failed"),
    Code.EMAIL_OCCUPIED: CodeMessage(zh="邮箱已被占用", en="Email is occupied"),
    Code.EMPTY_CONTENT: CodeMessage(zh="内容不能为空", en="Content cannot be empty"),
    Code.INVALID_TITLE: CodeMessage(zh="标题格式错误", en="Title format error"),
    Code.INVALID_LANGUAGE: CodeMessage(zh="无效的语言", en="Invalid language"),
    Code.ONE_USER_MODE: CodeMessage(zh="单用户模式，不支持注册", en="Single user mode, registration is not supported"),
    Code.INVALID_PASSWORD: CodeMessage(zh="密码格式错误", en="Password format error"),
    Code.CAPTCHA_ERROR: CodeMessage(zh="验证码输入错误", en="Captcha not match"),
    Code.CAPTCHA_EXPIRED: CodeMessage(zh="验证码已过期", en="Captcha expired"),
    Code.NOTE_EXCEED_MAX_LENGTH: CodeMessage(zh="内容超过最大长度", en="Content exceed max length"),
}

DEFAULT_USER = {
    "nickname": "rethink",
    "email": "rethink@rethink.run",
    "avatar": "",
}


@unique
class Language(Enum):
    EN = "en"
    ZH = "zh"

    def __str__(self):
        return self.value

    @classmethod
    def from_str(cls, s: str):
        if s == "en":
            return cls.EN
        elif s == "zh":
            return cls.ZH
        else:
            raise ValueError(f"Invalid language: {s}")

    @classmethod
    def is_valid(cls, s: str):
        try:
            cls.from_str(s)
            return True
        except ValueError:
            return False


def get_msg_by_code(code: Code, language: str = Language.EN.value):
    msg = CODE_MESSAGES[code]
    if language == Language.ZH.value:
        return msg.zh
    elif language == Language.EN.value:
        return msg.en
    else:
        raise ValueError(f"Invalid language: {language}")


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


NEW_USER_DEFAULT_NODES = {
    Language.EN.value: [
        dedent("""\
        # How do I record
        
        I like to record freely and without any restrictions.
        """),
        dedent("""\
        Welcome to Rethink
        
        Rethink is a knowledge management system. You can take node and manage your them here.

        Use @, you can link any record to create associations. For example [@How do I record](/n/{}) .

        Rethink also supports markdown syntax, allowing you to record richer expressions.
        """),
    ],
    Language.ZH.value: [
        dedent("""\
        # 我如何记录
        
        我喜欢自由自在的记录，不受任何限制。
        """),
        dedent("""\
        欢迎使用 Rethink
        
        Rethink 是一个知识管理系统，你可以在这里记录你的知识，管理你的记录。

        使用 @，你就可以链接任意的记录，创建联想。比如 [@我如何记录](/n/{}) 。

        Rethink 同样也支持 markdown 语法，让你可以记录更丰富的表达。
        """),
    ]
}
