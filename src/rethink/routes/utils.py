import time
from functools import wraps
from typing import Optional

from fastapi import HTTPException, Header, Depends
from fastapi.params import Path
from starlette.status import HTTP_403_FORBIDDEN
from typing_extensions import Annotated

from rethink import const, config
from rethink.controllers.utils import Headers, process_headers
from rethink.logger import logger

REFERER_PREFIX = f"https://{const.DOMAIN}"


def measure_time_spend(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            td = kwargs["td"]
            req_id = td.request_id
        except KeyError:
            req_id = ""

        req_s = str(kwargs.get("req", ""))
        uid = ""
        code = ""
        if "token_decode" in kwargs:
            uid = kwargs["token_decode"].uid
            code = kwargs["token_decode"].code
        req_s = req_s[:200] + "..." if len(req_s) > 200 else req_s
        if func.__name__ not in ["login", "reset_password", "register"]:
            logger.debug(f"REQ: reqId='{req_id}' | uid='{uid}' | api='{func.__name__}' | code='{code}' | {req_s}")

        resp = await func(*args, **kwargs)
        t1 = time.perf_counter()
        try:
            req_id = resp.requestId
        except AttributeError:
            req_id = ""
        logger.debug(f"RESP: reqId='{req_id}' | uid='{uid}' | api='{func.__name__}' | spend={t1 - t0:.4f}s")
        return resp

    return wrapper


def verify_referer(referer: Optional[str] = Header(None)):
    if config.get_settings().VERIFY_REFERER and not referer.startswith(REFERER_PREFIX):
        logger.error(f"referer={referer} not startswith {REFERER_PREFIX}")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid referer",
        )
    return referer


ANNOTATED_HEADERS = Annotated[Headers, Depends(process_headers)]
ANNOTATED_NID = Annotated[str, Path(title="The ID of node", max_length=const.NID_MAX_LENGTH, min_length=8)]
ANNOTATED_PID = Annotated[str, Path(title="The ID of plugin", max_length=const.PLUGIN_ID_MAX_LENGTH)]
ANNOTATED_FID = Annotated[str, Path(title="The ID of file", max_length=const.FID_MAX_LENGTH)]
DEPENDS_REFERER = Depends(verify_referer)
