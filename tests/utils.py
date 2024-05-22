import os
import shutil
from pathlib import Path

from retk import config


def set_env(file=".env.test.local"):
    config.get_settings.cache_clear()
    with open(Path(__file__).parent.parent / file, "r") as f:
        if file.startswith(".env.test"):
            os.environ["VUE_APP_MODE"] = "local"
            os.environ["VUE_APP_API_URL"] = "http//127.0.0.1:8000"
        if file.endswith(".local"):
            tmp = Path(__file__).parent / "tmp"
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir(exist_ok=True)
            os.environ["RETHINK_LOCAL_STORAGE_PATH"] = str(tmp)
        cs = f.readlines()
        for c in cs:
            k, v = c.split("=")
            os.environ[k] = v.strip()


def drop_env(file=".env.test.local"):
    config.get_settings.cache_clear()
    try:
        os.environ.pop("VUE_APP_MODE")
        os.environ.pop("VUE_APP_API_URL")
    except KeyError:
        pass
    try:
        tmp = os.environ.pop("RETHINK_LOCAL_STORAGE_PATH")
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    except KeyError:
        pass

    with open(Path(__file__).parent.parent / file, "r") as f:
        cs = f.readlines()
        for c in cs:
            k, _ = c.split("=")
            os.environ.pop(k)


def skip_no_connect(f):
    skip_no_connect.skip = False

    async def wrapper(*args, **kwargs):
        if skip_no_connect.skip:
            return
        return await f(*args, **kwargs)

    return wrapper
