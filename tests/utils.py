import os
import shutil
from pathlib import Path

from rethink import config


def set_env(file=".env.test.local"):
    config.get_settings.cache_clear()
    with open(Path(__file__).parent.parent / file, "r") as f:
        if file.startswith(".env.test"):
            tmp = Path(__file__).parent / "tmp"
            tmp.mkdir(exist_ok=True)
            os.environ["VUE_APP_MODE"] = "local"
            os.environ["LOCAL_STORAGE_PATH"] = str(tmp)
        cs = f.readlines()
        for c in cs:
            k, v = c.split("=")
            os.environ[k] = v.strip()


def drop_env(file=".env.test.local"):
    try:
        os.environ.pop("VUE_APP_MODE")
    except KeyError:
        pass
    tmp = os.environ.pop("LOCAL_STORAGE_PATH")
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)

    with open(Path(__file__).parent.parent / file, "r") as f:
        cs = f.readlines()
        for c in cs:
            k, _ = c.split("=")
            os.environ.pop(k)
