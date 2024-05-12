from typing import Tuple, Optional

import httpx

from retk import const
from retk.logger import logger
from retk.utils import ASYNC_CLIENT_HEADERS


def parse_version(version: str) -> Optional[Tuple[int, int, int]]:
    vs = version.split(".")
    if len(vs) != 3:
        return None
    try:
        vs = (int(vs[0]), int(vs[1]), int(vs[2]))
    except ValueError:
        return None
    return vs


async def get_latest_pkg_version() -> Tuple[Tuple[int, int, int], const.CodeEnum]:
    url = 'https://pypi.org/pypi/retk/json'
    default_version = (0, 0, 0)
    async with httpx.AsyncClient() as ac:
        try:
            response = await ac.get(
                url=url,
                headers=ASYNC_CLIENT_HEADERS,
                follow_redirects=False,
                timeout=2.
            )
        except (
                httpx.ConnectTimeout,
                RuntimeError,
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.HTTPError
        ) as e:
            logger.debug(f"failed to get {url}: {e}")
            return default_version, const.CodeEnum.OPERATION_FAILED

    if response.status_code != 200:
        logger.debug(f"failed to get {url}: {response.status_code}, {response.text}")
        return default_version, const.CodeEnum.OPERATION_FAILED

    package_info = response.json()

    try:
        v = package_info['info']['version']
    except KeyError:
        logger.debug(f"failed to get {url}: {response.text}")
        return default_version, const.CodeEnum.OPERATION_FAILED
    vs = parse_version(v)
    if vs is None:
        logger.debug(f"failed to get {url}: {v}")
        return default_version, const.CodeEnum.OPERATION_FAILED
    return vs, const.CodeEnum.OK
