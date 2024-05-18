from pydantic import BaseModel, EmailStr, Field

from retk.const import settings, LanguageEnum


class TokenResponse(BaseModel):
    requestId: str
    token: str = ""


class SignupRequest(BaseModel):
    email: EmailStr = Field(max_length=settings.EMAIL_MAX_LENGTH)
    password: str = Field(max_length=settings.PASSWORD_MAX_LENGTH)
    verificationToken: str = Field(max_length=2000)
    verification: str = Field(max_length=10)
    language: LanguageEnum


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=settings.EMAIL_MAX_LENGTH)
    password: str = Field(max_length=settings.PASSWORD_MAX_LENGTH)
    language: LanguageEnum = LanguageEnum.EN


class EmailVerificationRequest(BaseModel):
    email: str = Field(max_length=settings.EMAIL_MAX_LENGTH)
    userExistOk: bool = Field(default=False)
    captchaToken: str = Field(max_length=2000)
    captchaCode: str = Field(max_length=10)
    language: LanguageEnum = LanguageEnum.EN


class ForgetPasswordRequest(BaseModel):
    email: str = Field(max_length=settings.EMAIL_MAX_LENGTH)
    newPassword: str = Field(max_length=settings.PASSWORD_MAX_LENGTH)
    verification: str = Field(max_length=10)
    verificationToken: str = Field(max_length=2000)
    language: LanguageEnum = LanguageEnum.EN
