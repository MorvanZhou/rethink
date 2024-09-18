import asyncio
import json
import time
from collections import OrderedDict
from datetime import timedelta
from functools import wraps
from typing import Callable
from typing import Union

from starlette.exceptions import HTTPException

from retk import const
from retk.config import is_local_db
from retk.core.statistic import add_user_behavior
from retk.models.tps import AuthedUser


class RateLimiter:
    def __init__(self, requests: int, period: Union[int, float, timedelta]):
        if isinstance(period, (int, float)):
            period = timedelta(seconds=period)
        self.max_tokens = requests
        self.period = period
        self.tokens = requests
        self.last_refill = time.monotonic()

    async def __aenter__(self):
        while self.tokens < 1:
            await asyncio.sleep(0.1)
            now = time.monotonic()
            elapsed_time = now - self.last_refill
            if elapsed_time > self.period.total_seconds():
                self.tokens = self.max_tokens
                self.last_refill = now
                break
        self.tokens -= 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class ConcurrentLimiter:
    def __init__(self, n: int):
        self.semaphore = asyncio.Semaphore(n)

    async def __aenter__(self):
        await self.semaphore.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.semaphore.release()
        return False


def req_limit(requests: int, in_seconds: int):
    rate_limiter = OrderedDict()

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if is_local_db():
                return await func(*args, **kwargs)

            au: AuthedUser = kwargs.get('au')
            ip: str = kwargs.get('ip')
            if not au:
                if not ip:
                    raise HTTPException(status_code=400, detail="Bad Request: no au and ip")
                key = ip
            else:
                key = au.u.id

            current_time = time.time()
            window_start = current_time - in_seconds
            try:
                user_visit = rate_limiter.pop(key)
            except KeyError:
                user_visit = []
                rate_limiter[key] = user_visit
            else:
                rate_limiter[key] = [timestamp for timestamp in user_visit if timestamp > window_start]

            # remove expired keys
            for k in list(rate_limiter.keys()):
                try:
                    if rate_limiter[k][-1] > window_start:
                        break
                except IndexError:
                    break

                rate_limiter.pop(k)

            # check if rate limit exceeded
            if len(user_visit) >= requests:
                await add_user_behavior(
                    uid=key if au else "",
                    type_=const.UserBehaviorTypeEnum.RATE_LIMIT_EXCEEDED,
                    remark=json.dumps({"ip": ip if ip else "", "au": au.u.id if au else "", "func": func.__name__}),
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded: max {requests} requests in {in_seconds} seconds"
                )

            res = await func(*args, **kwargs)

            rate_limiter[key].append(current_time)
            return res

        return wrapper

    return decorator
