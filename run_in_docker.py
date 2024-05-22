import os

import uvicorn

from retk.run import _plugins_start_on_schedule


def main():
    os.environ["VUE_APP_API_URL"] = os.environ.get("API_URL")
    os.environ["VUE_APP_MODE"] = "local"

    os.environ["RETHINK_DEFAULT_LANGUAGE"] = os.environ.get("APP_LANGUAGE")
    os.environ["RETHINK_LOCAL_STORAGE_PATH"] = os.getcwd()
    os.environ["RETHINK_SERVER_HEADLESS"] = "0"
    os.environ["RETHINK_SERVER_DEBUG"] = "true"

    pw = os.environ.get("APP_PASSWORD", "")
    if pw != "":
        if len(pw) < 6 or len(pw) > 20:
            raise ValueError("Password length should be between 6 and 20 characters!")
        os.environ["RETHINK_SERVER_PASSWORD"] = pw

    _plugins_start_on_schedule()
    uvicorn.run(
        "retk.application:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        workers=1,
        log_level="error",
        env_file=os.path.join(os.path.abspath(os.path.dirname(__file__)), "src", "retk", ".env.local"),
    )


if __name__ == "__main__":
    main()
