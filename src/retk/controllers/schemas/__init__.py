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
    manager,
    statistic,
    notice,
    ai,
    browser_extension,
)


class RequestIdResponse(BaseModel):
    requestId: str
