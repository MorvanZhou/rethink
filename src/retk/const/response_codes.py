from dataclasses import dataclass
from enum import IntEnum, unique
from typing import Dict

from .languages import LanguageEnum


@unique
class CodeEnum(IntEnum):
    OK = 0
    ACCOUNT_OR_PASSWORD_ERROR = 1
    INVALID_AUTH = 2
    EXPIRED_AUTH = 3
    USER_EXIST = 4
    NODE_EXIST = 5
    NODE_NOT_EXIST = 6
    OPERATION_FAILED = 7
    EMAIL_OCCUPIED = 8
    PLUGIN_NOT_FOUND = 9
    COS_ERROR = 10
    OLD_PASSWORD_ERROR = 11
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
    INVALID_SETTING = 22
    IMPORT_PROCESS_NOT_FINISHED = 23
    UPLOAD_TASK_TIMEOUT = 24
    USER_SPACE_NOT_ENOUGH = 25
    INVALID_EMAIL = 26
    URL_TOO_LONG = 27
    OAUTH_PROVIDER_NOT_FOUND = 28
    TASK_NOT_FOUND = 29
    ACCOUNT_EXIST_TRY_FORGET_PASSWORD = 30
    USER_DISABLED = 31
    NOT_PERMITTED = 32
    EXPIRED_OR_NO_ACCESS_TOKEN = 33
    USER_NOT_EXIST = 34
    INVALID_PARAMS = 35
    INVALID_SCHEDULE_JOB_ID = 36
    NOTICE_NOT_FOUND = 37


@dataclass
class CodeMessage:
    zh: str
    en: str


CODE_MESSAGES: Dict[CodeEnum, CodeMessage] = {
    CodeEnum.OK: CodeMessage(zh="成功", en="OK"),
    CodeEnum.ACCOUNT_OR_PASSWORD_ERROR: CodeMessage(zh="账号不存在或者密码错误", en="No such user or password error"),
    CodeEnum.INVALID_AUTH: CodeMessage(zh="无效的认证信息", en="Invalid authentication information"),
    CodeEnum.EXPIRED_AUTH: CodeMessage(zh="认证信息已过期", en="Authentication information has expired"),
    CodeEnum.USER_EXIST: CodeMessage(zh="用户已存在", en="User already exists"),
    CodeEnum.NODE_EXIST: CodeMessage(zh="节点已存在", en="Node already exists"),
    CodeEnum.NODE_NOT_EXIST: CodeMessage(zh="节点不存在", en="Node does not exist"),
    CodeEnum.OPERATION_FAILED: CodeMessage(zh="操作失败", en="Operation failed"),
    CodeEnum.EMAIL_OCCUPIED: CodeMessage(zh="邮箱已被占用", en="Email is occupied"),
    CodeEnum.PLUGIN_NOT_FOUND: CodeMessage(zh="插件未找到", en="Plugin not found"),
    CodeEnum.COS_ERROR: CodeMessage(zh="COS 错误", en="COS error"),
    CodeEnum.OLD_PASSWORD_ERROR: CodeMessage(zh="旧密码错误", en="Old password error"),
    CodeEnum.ONE_USER_MODE: CodeMessage(zh="单用户模式，不支持注册",
                                        en="Single user mode, registration is not supported"),
    CodeEnum.INVALID_PASSWORD: CodeMessage(zh="密码格式错误", en="Password format error"),
    CodeEnum.CAPTCHA_ERROR: CodeMessage(zh="验证码输入错误", en="Captcha not match"),
    CodeEnum.CAPTCHA_EXPIRED: CodeMessage(zh="验证码已过期", en="Captcha expired"),
    CodeEnum.NOTE_EXCEED_MAX_LENGTH: CodeMessage(zh="内容超过最大长度", en="Content exceed max length"),
    CodeEnum.INVALID_NODE_DISPLAY_METHOD: CodeMessage(zh="无效的展示方式", en="Invalid display method"),
    CodeEnum.TOO_MANY_FILES: CodeMessage(zh="文件数量过多", en="Too many files"),
    CodeEnum.TOO_LARGE_FILE: CodeMessage(zh="文件过大", en="Too large file"),
    CodeEnum.INVALID_FILE_TYPE: CodeMessage(zh="无效的文件类型", en="Invalid file type"),
    CodeEnum.FILE_OPEN_ERROR: CodeMessage(zh="文件打开失败", en="File open error"),
    CodeEnum.INVALID_SETTING: CodeMessage(zh="无效的设置", en="Invalid setting"),
    CodeEnum.IMPORT_PROCESS_NOT_FINISHED: CodeMessage(
        zh="正在完成上一批数据导入，请稍后再试",
        en="Last import process not finished, please try again later"),
    CodeEnum.UPLOAD_TASK_TIMEOUT: CodeMessage(zh="文件上传任务超时", en="Upload task timeout"),
    CodeEnum.USER_SPACE_NOT_ENOUGH: CodeMessage(zh="用户空间不足", en="User space not enough"),
    CodeEnum.INVALID_EMAIL: CodeMessage(zh="邮箱格式错误", en="Email format error"),
    CodeEnum.URL_TOO_LONG: CodeMessage(zh="URL字符太长", en="URL too long"),
    CodeEnum.OAUTH_PROVIDER_NOT_FOUND: CodeMessage(zh="未找到 OAuth 提供商", en="OAuth provider not found"),
    CodeEnum.TASK_NOT_FOUND: CodeMessage(zh="任务未找到", en="Task not found"),
    CodeEnum.ACCOUNT_EXIST_TRY_FORGET_PASSWORD: CodeMessage(
        zh="账户已存在，请尝试通过忘记密码找回",
        en="Account exists, try forget password to recover",
    ),
    CodeEnum.USER_DISABLED: CodeMessage(
        zh="因违反平台规则，此账户已被禁用",
        en="This account has been disabled due to violation of platform rules"
    ),
    CodeEnum.NOT_PERMITTED: CodeMessage(zh="无权限", en="Not permitted"),
    CodeEnum.EXPIRED_OR_NO_ACCESS_TOKEN: CodeMessage(zh="访问令牌已过期或失效",
                                                     en="Access token has expired or invalid"),
    CodeEnum.USER_NOT_EXIST: CodeMessage(zh="用户不存在", en="User does not exist"),
    CodeEnum.INVALID_PARAMS: CodeMessage(zh="无效参数", en="Invalid parameter"),
    CodeEnum.INVALID_SCHEDULE_JOB_ID: CodeMessage(zh="无效的任务 ID", en="Invalid schedule job ID"),
    CodeEnum.NOTICE_NOT_FOUND: CodeMessage(zh="通知未找到", en="Notice not found"),
}

CODE2STATUS_CODE: Dict[CodeEnum, int] = {
    CodeEnum.OK: 200,
    CodeEnum.ACCOUNT_OR_PASSWORD_ERROR: 401,
    CodeEnum.INVALID_AUTH: 401,
    CodeEnum.EXPIRED_AUTH: 401,
    CodeEnum.USER_EXIST: 422,
    CodeEnum.NODE_EXIST: 422,
    CodeEnum.NODE_NOT_EXIST: 404,
    CodeEnum.OPERATION_FAILED: 500,
    CodeEnum.EMAIL_OCCUPIED: 422,
    CodeEnum.PLUGIN_NOT_FOUND: 404,
    CodeEnum.COS_ERROR: 500,
    CodeEnum.OLD_PASSWORD_ERROR: 400,
    CodeEnum.ONE_USER_MODE: 403,
    CodeEnum.INVALID_PASSWORD: 400,
    CodeEnum.CAPTCHA_ERROR: 400,
    CodeEnum.CAPTCHA_EXPIRED: 400,
    CodeEnum.NOTE_EXCEED_MAX_LENGTH: 400,
    CodeEnum.INVALID_NODE_DISPLAY_METHOD: 400,
    CodeEnum.TOO_MANY_FILES: 400,
    CodeEnum.TOO_LARGE_FILE: 400,
    CodeEnum.INVALID_FILE_TYPE: 400,
    CodeEnum.FILE_OPEN_ERROR: 400,
    CodeEnum.INVALID_SETTING: 400,
    CodeEnum.IMPORT_PROCESS_NOT_FINISHED: 403,
    CodeEnum.UPLOAD_TASK_TIMEOUT: 408,
    CodeEnum.USER_SPACE_NOT_ENOUGH: 403,
    CodeEnum.INVALID_EMAIL: 400,
    CodeEnum.URL_TOO_LONG: 406,
    CodeEnum.OAUTH_PROVIDER_NOT_FOUND: 404,
    CodeEnum.TASK_NOT_FOUND: 404,
    CodeEnum.ACCOUNT_EXIST_TRY_FORGET_PASSWORD: 422,
    CodeEnum.USER_DISABLED: 403,
    CodeEnum.NOT_PERMITTED: 403,
    CodeEnum.EXPIRED_OR_NO_ACCESS_TOKEN: 200,
    CodeEnum.USER_NOT_EXIST: 404,
    CodeEnum.INVALID_PARAMS: 400,
    CodeEnum.INVALID_SCHEDULE_JOB_ID: 400,
    CodeEnum.NOTICE_NOT_FOUND: 404,
}


def get_msg_by_code(code: CodeEnum, language: str = LanguageEnum.EN.value):
    msg = CODE_MESSAGES[code]
    if language == LanguageEnum.ZH.value:
        return msg.zh
    elif language == LanguageEnum.EN.value:
        return msg.en
    else:
        raise ValueError(f"Invalid language: {language}")
