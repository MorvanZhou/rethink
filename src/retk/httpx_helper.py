from typing import Optional

import httpx

__ac: Optional[httpx.AsyncClient] = None


def get_async_client() -> httpx.AsyncClient:
    global __ac
    if __ac is None:
        __ac = httpx.AsyncClient()
    return __ac


async def close_async_client():
    global __ac
    if __ac is not None:
        await __ac.aclose()
        __ac = None
