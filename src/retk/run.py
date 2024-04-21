import datetime
import os
import threading
from pathlib import Path
from typing import Literal, Union

import uvicorn

from retk.plugins.base import event_plugin_map, Plugin
from retk.plugins.schedule.scheduler import scheduler
from retk.plugins.schedule.timing import Every


def _schedule_job(plugin: Plugin, on: bool = False):
    if plugin.schedule_timing is None or not plugin.activated:
        return

    if on:
        plugin.on_schedule()

    t = plugin.schedule_timing
    now = datetime.datetime.now()
    if t.every == Every.minute:
        next_time = now.replace(
            second=t.at_second, microsecond=0
        ) + datetime.timedelta(minutes=1)

    elif t.every == Every.hour:
        next_time = now.replace(
            minute=t.at_minute, second=0, microsecond=0
        ) + datetime.timedelta(hours=1)
    elif t.every == Every.day:
        next_time = now.replace(
            hour=t.at_hour, minute=t.at_minute, second=0, microsecond=0
        ) + datetime.timedelta(days=1)
    elif t.every == Every.month:
        next_month = now.month + 1
        year = now.year
        if next_month > 12:
            next_month = 1
            year = now.year + 1
        next_time = datetime.datetime(
            year, next_month, t.at_day, t.at_hour, t.at_minute, t.at_second
        )
    else:
        raise ValueError(f"Invalid schedule timing: {t}")
    scheduler.enterabs(next_time.timestamp(), 1, _schedule_job, (plugin, True))


def _start_on_schedule_plugins():
    ps = event_plugin_map["on_schedule"]
    if len(ps) == 0:
        return
    for plugin in ps:
        _schedule_job(plugin, on=False)
    td = threading.Thread(target=scheduler.run)
    td.start()
    return td


def run(
        path: Union[str, Path] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        language: Literal["en", "zh"] = "en",
        password: str = None,
        headless: bool = False,
        debug: bool = False,
):
    """
    Run the server.

    Args:
        path (str): the database path for text and file data.
            Rethink will create .data folder in this path, default is current working directory.
        host (str): server host, default is the localhost.
        port (int): server port, default is 8000.
        language (str): website language, default is English.
            Possible values are "en" and "zh".
        password (str): the password for the server. default is None. If a string is provided,
            the login page will appear.
        headless (bool): run the server in headless mode. if False, it will open a browser after startup.
            default is False.
        debug (bool): run the server in debug mode. default is False.

    Raises:
        FileNotFoundError: if the path not exists.
        NotADirectoryError: if the path is not a directory.
    """
    if path is None:
        path = os.getcwd()
    if isinstance(path, str):
        path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Path not exists: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")
    os.environ["VUE_APP_API_PORT"] = str(port)
    os.environ["VUE_APP_MODE"] = "local"
    os.environ["RETHINK_DEFAULT_LANGUAGE"] = language
    os.environ["RETHINK_LOCAL_STORAGE_PATH"] = str(path)
    os.environ["RETHINK_SERVER_HEADLESS"] = "1" if headless else "0"
    os.environ["RETHINK_SERVER_HOSTNAME"] = host
    os.environ["RETHINK_SERVER_DEBUG"] = "true" if debug else "false"
    if password is not None:
        l_pw = len(password)
        if l_pw < 6 or l_pw > 20:
            raise ValueError("Password length should be between 6 and 20 characters!")
        if len(password) < 8:
            print("Password is too short. The password is highly recommended to be at least 8 characters!")
        os.environ["RETHINK_SERVER_PASSWORD"] = password

    td = _start_on_schedule_plugins()

    uvicorn.run(
        "retk.application:app",
        host=host,
        port=port,
        reload=False,
        workers=1,
        log_level="error",
        env_file=os.path.join(os.path.abspath(os.path.dirname(__file__)), ".env.local"),
    )
    td.join()
