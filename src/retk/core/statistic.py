import asyncio
import json
from datetime import datetime
from pathlib import Path

from retk import const
from retk.config import is_local_db

try:
    import aiofiles
except ImportError:
    aiofiles = None


async def __write_new(path: Path, lock: asyncio.Lock):
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        async with lock:
            await f.write("")


async def __write_line_date(data: dict, path: Path, lock: asyncio.Lock):
    async with aiofiles.open(path, "a", encoding="utf-8") as f:
        record_str = json.dumps(data, ensure_ascii=False)
        async with lock:
            await f.write(f"{record_str}\n")


async def __manage_files(now: datetime, path: Path, lock: asyncio.Lock):
    par = path.parent
    if not par.exists():
        par.mkdir(parents=True, exist_ok=True)
        await __write_new(path, lock)

    # backup if too large

    # if the file is too large, rename it to current time and create a new one
    if path.stat().st_size > const.settings.MAX_USER_BEHAVIOR_LOG_SIZE:
        backup_file = path.parent / f"{now.strftime('%Y%m%d-%H%M%S')}.log"
        path.rename(backup_file)
        await __write_new(path, lock)


async def add_user_behavior(
        uid: str,
        type_: const.UserBehaviorTypeEnum,
        remark: str,
):
    if is_local_db() or aiofiles is None:
        return
    file = const.settings.ANALYTICS_DIR / "user_behavior" / f"behavior.log"
    lock = asyncio.Lock()
    now = datetime.now()
    await __manage_files(now, file, lock)
    await __write_line_date(
        data={
            "time": now.strftime('%Y-%m-%d %H:%M:%S'),
            "uid": uid,
            "type": type_.value,
            "remark": remark,
        },
        path=file,
        lock=lock
    )
