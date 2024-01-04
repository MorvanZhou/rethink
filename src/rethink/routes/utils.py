import time
from functools import wraps
from typing import Optional

from fastapi import HTTPException, Header
from starlette.status import HTTP_403_FORBIDDEN

from rethink import const, config
from rethink.logger import logger


REFERER_PREFIX = f"https://{const.DOMAIN}"


def measure_time_spend(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        req_id = ""
        req_s = ""
        if "req" in kwargs:
            req = kwargs["req"]
            try:
                req_id = req.requestId
            except AttributeError:
                req_id = ""
            req_s = str(req)
        if "rid" in kwargs:
            req_id = kwargs["rid"]
        uid = ""
        code = ""
        if "token_decode" in kwargs:
            uid = kwargs["token_decode"].uid
            code = kwargs["token_decode"].code
        req_s = req_s[:200] + "..." if len(req_s) > 200 else req_s
        if func.__name__ not in ["login", "reset_password", "register"]:
            logger.info(f"REQ: reqId='{req_id}' | uid='{uid}' | api='{func.__name__}' | code='{code}' | req='{req_s}'")

        resp = await func(*args, **kwargs)
        t1 = time.perf_counter()
        try:
            req_id = resp.requestId
        except AttributeError:
            req_id = ""
        logger.info(f"RESP: reqId='{req_id}' | uid='{uid}' | api='{func.__name__}' | spend={t1 - t0:.4f}s")
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
