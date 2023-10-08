import os
from pathlib import Path
from typing import Literal, Union

import uvicorn


def run(
        path: Union[str, Path] = None,
        host="127.0.0.1",
        port=8000,
        language: Literal["en", "zh"] = "en",
):
    """
    Run the server.

    Args:
        path: local storage path, default is current working directory.
        host: server host, default is the localhost.
        port: server port, default is 8000.
        language: website language, default is English.

    Returns:
        None
    """
    if path is None:
        path = os.getcwd()
    if isinstance(path, str):
        path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Path not exists: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")
    os.environ["LOCAL_STORAGE_PATH"] = str(path)
    os.environ["VUE_APP_API_PORT"] = str(port)
    os.environ["VUE_APP_MODE"] = "local"
    os.environ["VUE_APP_LANGUAGE"] = language
    uvicorn.run(
        "rethink.application:app",
        host=host,
        port=port,
        reload=False,
        workers=1,
        env_file=os.path.join(os.path.abspath(os.path.dirname(__file__)), ".env.local"),
    )
