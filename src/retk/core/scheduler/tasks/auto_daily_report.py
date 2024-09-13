import asyncio
import json
import os
import time
from datetime import datetime, timedelta

from bson.objectid import ObjectId

from retk import config, const
from retk.core.statistic import __write_line_date, __manage_files
from retk.models.client import init_mongo
from retk.models.coll import CollNameEnum

try:
    import aiofiles
except ImportError:
    aiofiles = None


def auto_daily_report():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(_auto_daily_report())
    loop.close()
    return res


async def _auto_daily_report():
    if config.is_local_db() or aiofiles is None:
        return
    file = const.settings.ANALYTICS_DIR / "daily_report" / "report.log"
    lock = asyncio.Lock()
    now = datetime.utcnow()
    # get last line efficiently
    if file.exists():
        async with aiofiles.open(file, "r", encoding="utf-8") as f:
            async with lock:
                try:
                    await f.seek(-2, os.SEEK_END)
                    while f.read(1) != "\n":
                        await f.seek(-2, os.SEEK_CUR)
                    last_line = await f.readline()
                except OSError:
                    last_line = ""
        try:
            last_record = json.loads(last_line)
        except json.JSONDecodeError:
            last_record = {}
    else:
        last_record = {}
    yesterday = (now - timedelta(days=1)).date()
    last_record_date = last_record.get("date", None)

    if last_record_date is not None:
        last_record_date = datetime.strptime(last_record_date, '%Y-%m-%d').date()
    else:
        last_record_date = yesterday - timedelta(days=1)

    if last_record_date >= yesterday:
        return

    await __manage_files(now, file, lock)

    _, db = init_mongo(connection_timeout=5)
    total_email_users = await db[CollNameEnum.users.value].count_documents(
        {"source": const.UserSourceEnum.EMAIL.value}
    )
    total_google_users = await db[CollNameEnum.users.value].count_documents(
        {"source": const.UserSourceEnum.GOOGLE.value}
    )
    total_github_users = await db[CollNameEnum.users.value].count_documents(
        {"source": const.UserSourceEnum.GITHUB.value}
    )
    total_users = total_email_users + total_google_users + total_github_users
    # date to int timestamp
    timestamp = time.mktime(last_record_date.timetuple())
    time_filter = ObjectId.from_datetime(datetime.utcfromtimestamp(timestamp))

    await __write_line_date(
        data={
            "date": now.strftime('%Y-%m-%d'),
            "totalUsers": total_users,
            "totalEmailUsers": total_email_users,
            "totalGoogleUsers": total_google_users,
            "totalGithubUsers": total_github_users,
            "newUsers": await db[CollNameEnum.users.value].count_documents({"_id": {"$gt": time_filter}}),
            "totalNodes": await db[CollNameEnum.nodes.value].count_documents({}),
            "newNodes": await db[CollNameEnum.nodes.value].count_documents({"_id": {"$gt": time_filter}}),
            "totalFiles": await db[CollNameEnum.user_file.value].count_documents({}),
        },
        path=file,
        lock=lock
    )
