import asyncio
import time
from datetime import timedelta
from typing import Union


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
