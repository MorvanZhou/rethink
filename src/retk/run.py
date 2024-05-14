import os
from pathlib import Path
from typing import Literal, Union

import uvicorn

from retk.core import scheduler
from retk.plugins.base import event_plugin_map


def _plugins_start_on_schedule():
    for plugin in event_plugin_map["on_schedule"]:
        if plugin.schedule_timing is None or not plugin.activated:
            continue
        kw = {}
        if plugin.schedule_timing.every == scheduler.timing.Every.minute:
            kw["second"] = plugin.schedule_timing.at_second
        elif plugin.schedule_timing.every == scheduler.timing.Every.hour:
            kw["second"] = plugin.schedule_timing.at_second
            kw["minute"] = plugin.schedule_timing.at_minute
        elif plugin.schedule_timing.every == scheduler.timing.Every.day:
            kw["second"] = plugin.schedule_timing.at_second
            kw["minute"] = plugin.schedule_timing.at_minute
            kw["hour"] = plugin.schedule_timing.at_hour
        elif plugin.schedule_timing.every == scheduler.timing.Every.month:
            kw["second"] = plugin.schedule_timing.at_second
            kw["minute"] = plugin.schedule_timing.at_minute
            kw["hour"] = plugin.schedule_timing.at_hour
            kw["day"] = plugin.schedule_timing.at_day
        scheduler.run_every_at(
            func=plugin.on_schedule,
            **kw,
            args=(plugin, True),
        )


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

    _plugins_start_on_schedule()
    uvicorn.run(
        "retk.application:app",
        host=host,
        port=port,
        reload=False,
        workers=1,
        log_level="error",
        env_file=os.path.join(os.path.abspath(os.path.dirname(__file__)), ".env.local"),
    )
