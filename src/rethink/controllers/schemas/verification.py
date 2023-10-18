from pydantic import BaseModel, NonNegativeInt

from rethink import const


class VerifyCaptchaRequest(BaseModel):
    token: str
    codeStr: str
    language: str = const.Language.EN.value
    requestId: str = ""


class VerifyCaptchaResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
