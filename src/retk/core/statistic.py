import json
from datetime import datetime

from retk import const
from retk.config import is_local_db

try:
    import aiofiles
except ImportError:
    aiofiles = None


async def add_user_behavior(
        uid: str,
        type_: const.UserBehaviorTypeEnum,
        remark: str,
):
    if is_local_db() or aiofiles is None:
        return
    current_log_file = const.settings.USER_BEHAVIOR_LOG_DIR / f"behavior.log"
    if not current_log_file.exists():
        const.settings.USER_BEHAVIOR_LOG_DIR.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(current_log_file, "w") as f:
            await f.write("")

    time_now = datetime.now()
    # if the file is too large, rename it to current time and create a new one
    if current_log_file.stat().st_size > const.settings.MAX_USER_BEHAVIOR_LOG_SIZE:
        backup_file = const.settings.USER_BEHAVIOR_LOG_DIR / f"{time_now.strftime('%Y%m%d-%H%M%S')}.log"
        current_log_file.rename(backup_file)
        async with aiofiles.open(current_log_file, "w") as f:
            await f.write("")

    async with aiofiles.open(current_log_file, "a") as f:
        record = {
            "time": time_now.strftime('%Y-%m-%d %H:%M:%S'),
            "uid": uid,
            "type": type_.value,
            "remark": remark,
        }
        record_str = json.dumps(record)
        await f.write(f"{record_str}\n")
