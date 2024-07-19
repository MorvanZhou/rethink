import asyncio
import time
import unittest
from datetime import timedelta
from unittest.mock import patch

import httpx

from retk.core.utils import ratelimiter


class UtilsTest(unittest.IsolatedAsyncioTestCase):

    @patch("httpx.AsyncClient.get")
    async def test_single_rate_limiter(self, mock_get):
        mock_get.return_value = "mock"
        rate_limiter = ratelimiter.RateLimiter(requests=5, period=timedelta(seconds=0.1))
        st = time.time()
        count = 0

        async def fetch(url: str):
            nonlocal count
            async with rate_limiter:
                async with httpx.AsyncClient() as client:
                    await client.get(url)
                    count += 1

        tasks = [fetch("https://xxx") for _ in range(11)]
        await asyncio.gather(*tasks)
        total_time = time.time() - st
        self.assertGreaterEqual(total_time, 0.29)
        # self.assertLess(total_time, 0.5)
        self.assertEqual(11, count)

    @patch("httpx.AsyncClient.get")
    async def test_rate_limiter(self, mock_get):
        mock_get.return_value = "mock"

        rate_limiter_1 = ratelimiter.RateLimiter(requests=15, period=timedelta(seconds=1))
        rate_limiter_2 = ratelimiter.RateLimiter(requests=5, period=timedelta(seconds=0.1))

        st = time.time()
        count = 0

        async def fetch(url: str):
            nonlocal count
            async with rate_limiter_1, rate_limiter_2:
                async with httpx.AsyncClient() as client:
                    await client.get(url)
                    count += 1

        tasks = [fetch("https://xxx") for _ in range(16)]
        await asyncio.gather(*tasks)
        total_time = time.time() - st
        self.assertGreaterEqual(total_time, 1)
        # self.assertLess(total_time, 2.5)
        self.assertEqual(16, count)

    async def test_concurrent_limiter(self):
        concurrent_limiter = ratelimiter.ConcurrentLimiter(n=2)
        st = time.time()
        count = 0

        async def fetch():
            nonlocal count
            async with concurrent_limiter:
                async with httpx.AsyncClient() as _:
                    await asyncio.sleep(0.1)
                    count += 1

        tasks = [fetch() for _ in range(5)]
        await asyncio.gather(*tasks)
        total_time = time.time() - st
        self.assertGreaterEqual(total_time, 0.29)
        # self.assertLess(total_time, 0.5)
        self.assertEqual(5, count)

    async def test_concurrent_with_rate_limiter(self):
        concurrent_limiter = ratelimiter.ConcurrentLimiter(n=2)
        rate_limiter = ratelimiter.RateLimiter(requests=3, period=timedelta(seconds=0.2))

        st = time.time()
        count = 0

        async def fetch():
            nonlocal count
            async with concurrent_limiter, rate_limiter:
                async with httpx.AsyncClient() as _:
                    await asyncio.sleep(0.1)
                    count += 1

        tasks = [fetch() for _ in range(4)]
        await asyncio.gather(*tasks)
        total_time = time.time() - st
        self.assertGreaterEqual(total_time, 0.29)
        # self.assertLess(total_time, 0.5)
        self.assertEqual(4, count)
