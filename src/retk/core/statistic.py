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
    async with aiofiles.open(path, "w") as f:
        async with lock:
            await f.write("")


async def add_user_behavior(
        uid: str,
        type_: const.UserBehaviorTypeEnum,
        remark: str,
):
    if is_local_db() or aiofiles is None:
        return
    current_log_file = const.settings.USER_BEHAVIOR_LOG_DIR / f"behavior.log"
    lock = asyncio.Lock()
    if not current_log_file.exists():
        const.settings.USER_BEHAVIOR_LOG_DIR.mkdir(parents=True, exist_ok=True)
        await __write_new(current_log_file, lock)

    time_now = datetime.now()
    # if the file is too large, rename it to current time and create a new one
    if current_log_file.stat().st_size > const.settings.MAX_USER_BEHAVIOR_LOG_SIZE:
        backup_file = const.settings.USER_BEHAVIOR_LOG_DIR / f"{time_now.strftime('%Y%m%d-%H%M%S')}.log"
        current_log_file.rename(backup_file)
        await __write_new(current_log_file, lock)

    async with aiofiles.open(current_log_file, "a") as f:
        record = {
            "time": time_now.strftime('%Y-%m-%d %H:%M:%S'),
            "uid": uid,
            "type": type_.value,
            "remark": remark,
        }
        record_str = json.dumps(record)
        async with lock:
            await f.write(f"{record_str}\n")
