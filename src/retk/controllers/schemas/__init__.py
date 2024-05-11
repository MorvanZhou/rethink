from pydantic import BaseModel

# flake8: noqa
from . import (
    account,
    user,
    node,
    recent,
    files,
    plugin,
    app_system,
    admin,
    statistic,
    notice,
)


class RequestIdResponse(BaseModel):
    requestId: str
