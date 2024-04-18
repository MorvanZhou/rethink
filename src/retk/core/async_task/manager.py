import threading
from enum import Enum
from queue import Queue

from retk.logger import logger
from . import (
    send_email,
)

_task_queue = Queue()


class TaskName(Enum):
    TEST = 0
    SEND_EMAIL = 1


_task_id_map = {
    TaskName.TEST.value: lambda x: f"test {x}",
    TaskName.SEND_EMAIL.value: send_email.task,
}

_task_id2name = {
    t.value: t.name for t in TaskName
}


def init():
    td = threading.Thread(target=task_thread_job, args=(_task_queue,), daemon=True)
    td.start()


def task_thread_job(q: Queue):
    while True:
        task_id: int
        task_id, args, kwarg = q.get()
        try:
            task = _task_id_map[task_id]
        except KeyError:
            logger.error(f"async task_id={task_id} not found")
            continue
        res = task(*args, **kwarg)
        task_name = _task_id2name[task_id]
        logger.debug(f"async task '{task_name}' done, res: {res}")


def put_task(task_name: TaskName, *args, **kwargs):
    _task_queue.put((task_name.value, args, kwargs))
