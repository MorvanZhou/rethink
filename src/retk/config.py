import datetime
from functools import lru_cache
from typing import Optional

import bcrypt
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import Field, DirectoryPath
from pydantic_settings import BaseSettings, SettingsConfigDict

from retk.logger import logger


class Settings(BaseSettings):
    # system settings
    ONE_USER: bool = Field(default=False, env='ONE_USER')
    RETHINK_SERVER_DEBUG: bool = Field(default=False, env='RETHINK_SERVER_DEBUG')
    VERIFY_REFERER: bool = Field(default=False, env='VERIFY_REFERER')
    PLUGINS: bool = Field(default=False, env='PLUGINS')
    RETHINK_LOCAL_STORAGE_PATH: Optional[DirectoryPath] = Field(env='RETHINK_LOCAL_STORAGE_PATH', default=None)
    MD_BACKUP_INTERVAL: int = Field(env="MD_BACKUP_INTERVAL", default=60 * 5)  # 5 minutes

    # database settings: MongoDB
    DB_NAME: str = Field(env='DB_NAME', default="")
    DB_USER: str = Field(env='DB_USER', default="")
    DB_PASSWORD: str = Field(env='DB_PASSWORD', default="")
    DB_HOST: str = Field(env='DB_HOST', default="")
    DB_PORT: int = Field(env='DB_PORT', default=-1)
    DB_SALT: str = Field(env='BD_SALT', default="")

    # database settings: ElasticSearch
    ES_USER: str = Field(env='ES_USER', default="")
    ES_PASSWORD: str = Field(env='ES_PASSWORD', default="")
    ES_HOSTS: str = Field(env='ES_HOSTS', default="")
    ES_INDEX_ALIAS: str = Field(env='ES_INDEX_ALIAS', default="")

    # database settings: COS
    COS_SECRET_ID: str = Field(env='COS_SECRET_ID', default="")
    COS_SECRET_KEY: str = Field(env="COS_SECRET_KEY", default="")
    COS_REGION: Optional[str] = Field(env="COS_REGION", default=None)
    COS_BUCKET_NAME: str = Field(env="COS_BUCKET_NAME", default="")
    COS_DOMAIN: Optional[str] = Field(env="COS_DOMAIN", default=None)

    # llm knowledge service settings
    LLM_KNOWLEDGE_SCHEDULE_MINUTES: int = Field(env='LLM_KNOWLEDGE_SCHEDULE_MINUTES', default=60)
    LLM_KNOWLEDGE_SUMMARY_SERVICE: str = Field(env='LLM_KNOWLEDGE_SUMMARY_SERVICE', default="")
    LLM_KNOWLEDGE_SUMMARY_MODEL: str = Field(env='LLM_KNOWLEDGE_SUMMARY_MODEL', default="")
    LLM_KNOWLEDGE_EXTEND_SERVICE: str = Field(env='LLM_KNOWLEDGE_EXTEND_SERVICE', default="")
    LLM_KNOWLEDGE_EXTEND_MODEL: str = Field(env='LLM_KNOWLEDGE_EXTEND_MODEL', default="")

    # hunyuan
    HUNYUAN_SECRET_ID: str = Field(env='HUNYUAN_SECRET_ID', default="")
    HUNYUAN_SECRET_KEY: str = Field(env='HUNYUAN_SECRET_KEY', default="")

    # aliyun
    ALIYUN_DASHSCOPE_API_KEY: str = Field(env='ALIYUN_DASHSCOPE_API_KEY', default="")

    # baidu
    BAIDU_QIANFAN_API_KEY: str = Field(env='BAIDU_QIANFAN_API_KEY', default="")
    BAIDU_QIANFAN_SECRET_KEY: str = Field(env='BAIDU_QIANFAN_SECRET_KEY', default="")

    # openai project api key
    OPENAI_API_KEY: str = Field(env='OPENAI_API_KEY', default="")

    # xfyun api
    XFYUN_API_SECRET: str = Field(env='XFYUN_API_SECRET', default="")
    XFYUN_API_KEY: str = Field(env='XFYUN_API_KEY', default="")

    # moonshot api
    MOONSHOT_API_KEY: str = Field(env='MOONSHOT_API_KEY', default="")
    MOONSHOT_CONCURRENCY: int = Field(env='MOONSHOT_CONCURRENCY', default=1)
    MOONSHOT_RPM: int = Field(env='MOONSHOT_RPM', default=3)
    MOONSHOT_TPM: int = Field(env='MOONSHOT_TPM', default=32_000)
    MOONSHOT_TPD: int = Field(env='MOONSHOT_TPD', default=1_500_000)

    # voclengine api
    VOLCENGINE_API_KEY: str = Field(env='VOLCENGINE_API_KEY', default="")
    VOLCENGINE_ENDPOINT_ID: str = Field(env='VOLCENGINE_ENDPOINT_ID', default="")

    # zhipu bigmodel
    BIGMODEL_API_KEY: str = Field(env='BIGMODEL_API_KEY', default="")
    BIGMODEL_CONCURRENCY: int = Field(env='BIGMODEL_CONCURRENCY', default=1)

    # Email client settings
    RETHINK_EMAIL: str = Field(env='RETHINK_EMAIL', default="")
    RETHINK_EMAIL_SECRET_ID: str = Field(env='RETHINK_EMAIL_SECRET_ID', default="")
    RETHINK_EMAIL_SECRET_KEY: str = Field(env='RETHINK_EMAIL_SECRET_KEY', default="")

    # OAuth settings
    OAUTH_REDIRECT_URL: str = Field(env='OAUTH_REDIRECT_URL', default="")
    OAUTH_CLIENT_ID_GITHUB: str = Field(env='OAUTH_CLIENT_ID_GITHUB', default="")
    OAUTH_CLIENT_SEC_GITHUB: str = Field(env='OAUTH_CLIENT_SEC_GITHUB', default="")
    OAUTH_API_TOKEN_GITHUB: str = Field(env='OAUTH_API_TOKEN_GITHUB', default="")
    OAUTH_CLIENT_ID_QQ: str = Field(env='OAUTH_CLIENT_ID_QQ', default="")
    OAUTH_CLIENT_SEC_QQ: str = Field(env='OAUTH_CLIENT_SEC_QQ', default="")
    OAUTH_CLIENT_ID_FACEBOOK: str = Field(env='OAUTH_CLIENT_ID_QQ', default="")
    OAUTH_CLIENT_SEC_FACEBOOK: str = Field(env='OAUTH_CLIENT_SEC_QQ', default="")
    OAUTH_CLIENT_ID_GOOGLE: str = Field(env='OAUTH_CLIENT_ID_GOOGLE', default="")
    OAUTH_CLIENT_SEC_GOOGLE: str = Field(env='OAUTH_CLIENT_SEC_GOOGLE', default="")

    # auth secret
    JWT_KEY: bytes = Field(env='JWT_KEY', default=b"")
    JWT_KEY_PUB: bytes = Field(env='JWT_KEY_PUB', default=b"")
    JWT_REFRESH_EXPIRED_DAYS: int = Field(default=1, env='JWT_REFRESH_EXPIRED_DAYS')
    JWT_ACCESS_EXPIRED_MINS: int = Field(default=5, env='JWT_ACCESS_EXPIRED_MINS')
    REFRESH_TOKEN_EXPIRE_DELTA: datetime.timedelta = Field(default=datetime.timedelta(days=1))
    ACCESS_TOKEN_EXPIRE_DELTA: datetime.timedelta = Field(default=datetime.timedelta(minutes=15))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
    )

    def __init__(self):
        super().__init__()
        if self.RETHINK_SERVER_DEBUG:
            logger.setLevel("DEBUG")

        if self.RETHINK_LOCAL_STORAGE_PATH is None and self.DB_HOST == "":
            raise ValueError("RETHINK_LOCAL_STORAGE_PATH and DB_HOST cannot be empty at the same time")
        if self.DB_SALT == "":
            self.DB_SALT = bcrypt.gensalt(4).decode("utf-8")
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

        self.REFRESH_TOKEN_EXPIRE_DELTA = datetime.timedelta(days=self.JWT_REFRESH_EXPIRED_DAYS)
        self.ACCESS_TOKEN_EXPIRE_DELTA = datetime.timedelta(minutes=self.JWT_ACCESS_EXPIRED_MINS)

        if self.COS_DOMAIN == "":
            self.COS_DOMAIN = None
        if self.COS_REGION == "":
            self.COS_REGION = None


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def is_local_db() -> bool:
    return get_settings().RETHINK_LOCAL_STORAGE_PATH is not None
