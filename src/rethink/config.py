import datetime
from functools import lru_cache
from typing import Optional

import bcrypt
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import Field, DirectoryPath
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ONE_USER: bool = Field(default=1, env='ONE_USER')
    LOCAL_STORAGE_PATH: Optional[DirectoryPath] = Field(env='LOCAL_STORAGE_PATH', default=None)
    DB_NAME: str = Field(env='DB_NAME', default="")
    DB_USER: str = Field(env='DB_USER', default="")
    DB_PASSWORD: str = Field(env='DB_PASSWORD', default="")
    DB_HOST: str = Field(env='DB_HOST', default="")
    DB_PORT: int = Field(env='DB_PORT', default=-1)
    DB_SALT: bytes = Field(env='DB_SALT', default=b"")
    JWT_KEY: bytes = Field(env='JWT_KEY', default=b"")
    JWT_KEY_PUB: bytes = Field(env='JWT_KEY_PUB', default=b"")
    JWT_EXPIRED_DAYS: int = Field(default=1, env='JWT_EXPIRED_DAYS')
    JWT_EXPIRED_DELTA: datetime.timedelta = Field(default=datetime.timedelta(days=1), env='JWT_EXPIRED_DELTA')
    OAUTH_REDIRECT_URL: str = Field(env='OAUTH_REDIRECT_URL', default="")
    OAUTH_CLIENT_ID_GITHUB: str = Field(env='OAUTH_CLIENT_ID_GITHUB', default="")
    OAUTH_CLIENT_SEC_GITHUB: str = Field(env='OAUTH_CLIENT_SEC_GITHUB', default="")
    OAUTH_CLIENT_ID_QQ: str = Field(env='OAUTH_CLIENT_ID_QQ', default="")
    OAUTH_CLIENT_SEC_QQ: str = Field(env='OAUTH_CLIENT_SEC_QQ', default="")
    OAUTH_CLIENT_ID_FACEBOOK: str = Field(env='OAUTH_CLIENT_ID_QQ', default="")
    OAUTH_CLIENT_SEC_FACEBOOK: str = Field(env='OAUTH_CLIENT_SEC_QQ', default="")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
    )

    def __init__(self):
        super().__init__()
        if self.LOCAL_STORAGE_PATH is None and self.DB_HOST == "":
            raise ValueError("LOCAL_STORAGE_PATH and DB_HOST cannot be empty at the same time")
        if self.DB_SALT == b"":
            self.DB_SALT = bcrypt.gensalt(4)
        if self.JWT_KEY == b"" or self.JWT_KEY_PUB == b"":
            key = rsa.generate_private_key(
                backend=crypto_default_backend(),
                public_exponent=65537,
                key_size=4096
            )
            self.JWT_KEY = key.private_bytes(
                crypto_serialization.Encoding.PEM,
                crypto_serialization.PrivateFormat.PKCS8,
                crypto_serialization.NoEncryption()
            )

            self.JWT_KEY_PUB = key.public_key().public_bytes(
                crypto_serialization.Encoding.OpenSSH,
                crypto_serialization.PublicFormat.OpenSSH
            )
        self.JWT_EXPIRED_DELTA = datetime.timedelta(days=self.JWT_EXPIRED_DAYS)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def is_local_db() -> bool:
    return get_settings().LOCAL_STORAGE_PATH is not None
