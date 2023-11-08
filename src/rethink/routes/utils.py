import time
from functools import wraps

from rethink.logger import logger


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
