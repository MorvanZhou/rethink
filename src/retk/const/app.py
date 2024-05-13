from enum import Enum, unique, IntEnum


@unique
class AppThemeEnum(str, Enum):
    DARK = "dark"
    LIGHT = "light"

    def __str__(self):
        return self.value

    @classmethod
    def is_valid(cls, item: str):
        return item in [v.value for v in cls.__members__.values()]


@unique
class EditorModeEnum(str, Enum):
    WYSIWYG = "wysiwyg"
    IR = "ir"

    def __str__(self):
        return self.value

    @classmethod
    def is_valid(cls, item: str):
        return item in [v.value for v in cls.__members__.values()]


@unique
class EditorCodeThemeEnum(str, Enum):
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
class EditorFontSizeEnum(IntEnum):
    MAX = 30
    MIN = 10

    @classmethod
    def is_valid(cls, item: int):
        return cls.MIN.value <= item <= cls.MAX.value


class FileTypesEnum(Enum):
    IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
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
class ValidUploadedFilePrefixEnum(Enum):
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
