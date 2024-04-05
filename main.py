import argparse
import os

import uvicorn

parser = argparse.ArgumentParser(description="Run the backend server.")
parser.add_argument("--host", type=str, default="127.0.0.1", help="Host IP address.")
parser.add_argument("--port", type=int, default=8000, help="Port number.")
parser.add_argument("--reload", action="store_true", help="Enable auto-reload.")
parser.add_argument("--workers", type=int, default=1, help="Number of workers.")
parser.add_argument("--mode", type=str, default="local", help="Server mode.")
parser.add_argument("--env-file", type=str, default=".env.local", help="Environment file path.")
parser.add_argument("--headless", action="store_true", help="Run the server in headless mode.")
parser.add_argument("--debug", action="store_true", help="Run the server in debug mode.")
parser.add_argument("--password", type=str, required=False, help="The password for the server.")

args = parser.parse_args(["--mode", "local", "--headless", "--password", "123456"])

if __name__ == "__main__":
    os.environ["VUE_APP_API_PORT"] = str(args.port)
    if os.environ.get("VUE_APP_MODE") is None:
        os.environ["VUE_APP_MODE"] = args.mode

    os.environ["RETHINK_SERVER_HEADLESS"] = "1" if args.headless else "0"
    os.environ["RETHINK_SERVER_HOSTNAME"] = args.host
    os.environ["RETHINK_SERVER_DEBUG"] = "true" if args.debug else "false"
    if args.password is not None:
        os.environ["RETHINK_SERVER_PASSWORD"] = args.password
    uvicorn.run(
        "rethink.application:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        env_file=args.env_file,
    )
