import asyncio
import multiprocessing
import traceback
from typing import Optional

from retk.logger import logger
from .obsidian.task import upload_obsidian_task
from .text.task import update_text_task

__process: Optional[multiprocessing.Process] = None
__ctx = multiprocessing.get_context('spawn')
QUEUE = __ctx.Queue()


def __async_task(queue: multiprocessing.Queue):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    while True:
        item = queue.get()
        task = item.pop("task")
        if task == "md":
            func = update_text_task
        elif task == "obsidian":
            func = upload_obsidian_task
        else:
            logger.error(f"unknown task: {task}")
            continue
        try:
            loop.run_until_complete(func(**item))
        except Exception:  # pylint: disable=broad-except
            msg = traceback.format_exc()
            oneline = msg.replace("\n", "\\n")
            logger.error(f"async task error: {oneline}")
    loop.close()


def init():
    global __process
    __process = __ctx.Process(
        target=__async_task,
        args=(QUEUE,),
        daemon=True,
    )
    __process.start()
    logger.info("async task process stopped")


def stop():
    global __process
    if __process is None:
        return
    __process.terminate()
    __process.join()
    __process = None
    logger.info("async task process stopped")
