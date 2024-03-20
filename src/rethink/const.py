# flake8: noqa
from dataclasses import dataclass
from enum import Enum, auto, unique
from pathlib import Path
from textwrap import dedent

DOMAIN = "rethink.run"
RETHINK_DIR = Path(__file__).parent
FRONTEND_DIR = RETHINK_DIR / "dist-local"
MD_MAX_LENGTH = 100_000
REQUEST_ID_MAX_LENGTH = 50
NID_MAX_LENGTH = 30
SEARCH_QUERY_MAX_LENGTH = 100
RECOMMEND_CONTENT_MAX_LENGTH = 200
EMAIL_MAX_LENGTH = 100
PASSWORD_MAX_LENGTH = 20
NICKNAME_MAX_LENGTH = 20
IMG_RESIZE_THRESHOLD = 1024 * 1024 * 3  # 3MB
MAX_UPLOAD_FILE_SIZE = 1024 * 1024 * 50  # 50MB
PLUGIN_ID_MAX_LENGTH = 40


class NodeType(Enum):
    FILE = 0
    MARKDOWN = auto()


@unique
class Code(Enum):
    OK = 0
    ACCOUNT_OR_PASSWORD_ERROR = 1
    INVALID_AUTH = 2
    EXPIRED_AUTH = 3
    USER_EXIST = 4
    NODE_EXIST = 5
    NODE_NOT_EXIST = 6
    OPERATION_FAILED = 7
    EMAIL_OCCUPIED = 8
    EMPTY_CONTENT = 9
    INVALID_TITLE = 10
    INVALID_LANGUAGE = 11
    ONE_USER_MODE = 12
    INVALID_PASSWORD = 13
    CAPTCHA_ERROR = 14
    CAPTCHA_EXPIRED = 15
    NOTE_EXCEED_MAX_LENGTH = 16
    INVALID_NODE_DISPLAY_METHOD = 17
    TOO_MANY_FILES = 18
    TOO_LARGE_FILE = 19
    INVALID_FILE_TYPE = 20
    FILE_OPEN_ERROR = 21
    FILENAME_EXIST = 22
    IMPORT_PROCESS_NOT_FINISHED = 23
    UPLOAD_TASK_TIMEOUT = 24
    USER_SPACE_NOT_ENOUGH = 25
    INVALID_NODE_DISPLAY_SORT_KEY = 26
    INVALID_EMAIL = 27
    REQUEST_INPUT_ERROR = 28
    INVALID_SETTING = 29
    OLD_PASSWORD_ERROR = 30
    PLUGIN_NOT_FOUND = 31


INT_CODE_MAP = {
    c.value: c for c in Code
}


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
    Code.INVALID_NODE_DISPLAY_METHOD: CodeMessage(zh="无效的展示方式", en="Invalid display method"),
    Code.TOO_MANY_FILES: CodeMessage(zh="文件数量过多", en="Too many files"),
    Code.TOO_LARGE_FILE: CodeMessage(zh="文件过大", en="Too large file"),
    Code.INVALID_FILE_TYPE: CodeMessage(zh="无效的文件类型", en="Invalid file type"),
    Code.FILE_OPEN_ERROR: CodeMessage(zh="文件打开失败", en="File open error"),
    Code.FILENAME_EXIST: CodeMessage(zh="文件名已存在", en="Filename already exists"),
    Code.IMPORT_PROCESS_NOT_FINISHED: CodeMessage(
        zh="正在完成上一批数据导入，请稍后再试",
        en="Last import process not finished, please try again later"),
    Code.UPLOAD_TASK_TIMEOUT: CodeMessage(zh="文件上传任务超时", en="Upload task timeout"),
    Code.USER_SPACE_NOT_ENOUGH: CodeMessage(zh="用户空间不足", en="User space not enough"),
    Code.INVALID_NODE_DISPLAY_SORT_KEY: CodeMessage(zh="无效的排序方式", en="Invalid sort key"),
    Code.INVALID_EMAIL: CodeMessage(zh="邮箱格式错误", en="Email format error"),
    Code.REQUEST_INPUT_ERROR: CodeMessage(zh="请求输入错误", en="Request input error"),
    Code.INVALID_SETTING: CodeMessage(zh="无效的设置", en="Invalid setting"),
    Code.OLD_PASSWORD_ERROR: CodeMessage(zh="旧密码错误", en="Old password error"),
    Code.PLUGIN_NOT_FOUND: CodeMessage(zh="插件未找到", en="Plugin not found"),
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
    def is_valid(cls, item: str):
        return item in [v.value for v in cls.__members__.values()]


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
        
        Rethink is a Knowledge Management System. You can take node and manage them here.

        Use @ to link between notes. For example [@How do I record](/n/{}) .

        Rethink also supports markdown syntax, for example:
        
        # My task list
        
        - [x] task 1
        - [ ] task 2
        - [ ] task 3
        
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

        Rethink 同样也支持 markdown 语法，让你可以记录更丰富的表达。比如：
        
        # 我的任务清单
        
        - [x] 任务 1
        - [ ] 任务 2
        - [ ] 任务 3
        
        """),
    ]
}


class NodeDisplayMethod(Enum):
    CARD = 0
    LIST = auto()  # 1


@dataclass
class UserConfig:
    id: int
    max_store_space: int


class UserType:
    NORMAL = UserConfig(
        id=0,
        max_store_space=1024 * 1024 * 500,  # 500MB
    )
    ADMIN = UserConfig(
        id=1,
        max_store_space=1024 * 1024 * 1024 * 100,  # 100GB
    )

    def id2config(self, _id: int):
        if _id == self.NORMAL.id:
            return self.NORMAL
        elif _id == self.ADMIN.id:
            return self.ADMIN
        else:
            raise ValueError(f"Invalid user type: {_id}")


USER_TYPE = UserType()


@unique
class AppTheme(Enum):
    DARK = "dark"
    LIGHT = "light"

    def __str__(self):
        return self.value

    @classmethod
    def is_valid(cls, item: str):
        return item in [v.value for v in cls.__members__.values()]


@unique
class EditorMode(Enum):
    WYSIWYG = "wysiwyg"
    IR = "ir"

    def __str__(self):
        return self.value

    @classmethod
    def is_valid(cls, item: str):
        return item in [v.value for v in cls.__members__.values()]


@unique
class EditorCodeTheme(Enum):
    DRACULA = "dracula"
    GITHUB = "github"
    EMACS = "emacs"
    TANGO = "tango"

    def __str__(self):
        return self.value

    @classmethod
    def is_valid(cls, item: str):
        return item in [v.value for v in cls.__members__.values()]


@unique
class EditorFontSize(Enum):
    MAX = 30
    MIN = 10

    @classmethod
    def is_valid(cls, item: int):
        return cls.MIN.value <= item <= cls.MAX.value


class FileTypes(Enum):
    IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    DOC = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
    PLAIN = {".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".toml"}
    PDF = {".pdf"}
    VIDEO = {".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv"}
    AUDIO = {".mp3", ".wav", ".wma", ".ogg", ".aac", ".flac"}
    UNKNOWN = "unknown"

    @classmethod
    def get_type(cls, ext: str):
        for t in cls.__members__.values():
            if ext in t.value:
                return t
        return cls.UNKNOWN


@unique
class ValidUploadedFilePrefix(Enum):
    # image/*,video/*,audio/*,application/pdf,text/plain,text/markdown
    IMAGE = "image/"
    VIDEO = "video/"
    AUDIO = "audio/"
    TEXT = "text/"
    PDF = "application/pdf"
    DOC = "application/msword"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    XLS = "application/vnd.ms-excel"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    PPT = "application/vnd.ms-powerpoint"
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    def __str__(self):
        return self.value

    @classmethod
    def is_valid(cls, item: str):
        for pre in [v.value for v in cls.__members__.values()]:
            if pre.endswith("/") and item.startswith(pre):
                return True
            elif pre == item:
                return True
        return False
