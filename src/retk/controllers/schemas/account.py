from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from retk import const


class TokenResponse(BaseModel):
    requestId: str
    token: str = ""


class SignupRequest(BaseModel):
    email: EmailStr = Field(max_length=const.EMAIL_MAX_LENGTH)
    password: str = Field(max_length=const.PASSWORD_MAX_LENGTH)
    captchaToken: str = Field(max_length=2000)
    captchaCode: str = Field(max_length=10)
    language: Literal["en", "zh"]


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=const.EMAIL_MAX_LENGTH)
    password: str = Field(max_length=const.PASSWORD_MAX_LENGTH)
    language: Literal["en", "zh"] = const.Language.EN.value


class EmailVerificationRequest(BaseModel):
    email: str = Field(max_length=const.EMAIL_MAX_LENGTH)
    userExistOk: bool = Field(type=bool, default=False)
    captchaToken: str = Field(max_length=2000)
    captchaCode: str = Field(max_length=10)
    language: Literal["en", "zh"] = const.Language.EN.value


class ForgetPasswordRequest(BaseModel):
    email: str = Field(max_length=const.EMAIL_MAX_LENGTH)
    newPassword: str = Field(max_length=const.PASSWORD_MAX_LENGTH)
    verification: str = Field(max_length=const.PASSWORD_MAX_LENGTH)
    verificationToken: str = Field(max_length=2000)
    language: Literal["en", "zh"] = const.Language.EN.value
