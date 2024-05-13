from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Optional, Tuple, Dict, Any, List

from apscheduler.schedulers.background import BackgroundScheduler

from retk.const.settings import MAX_SCHEDULE_JOB_INFO_LEN

"""
- BlockingScheduler:
 use when the scheduler is the only thing running in your process
 
- BackgroundScheduler:
 use when you’re not using any of the frameworks below, 
 and want the scheduler to run in the background inside your application
 
- AsyncIOScheduler:
 use if your application uses the asyncio module
 
- GeventScheduler:
 use if your application uses gevent
 
- TornadoScheduler:
 use if you’re building a Tornado application
 
- TwistedScheduler: 
 use if you’re building a Twisted application
 
- QtScheduler:
 use if you’re building a Qt application
"""


@dataclass
class JobInfo:
    type: str
    args: Tuple
    kwargs: Dict[str, Any]
    execute_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    finished_return: Optional[str] = None
    create_at: datetime = None

    def __post_init__(self):
        self.created_at = datetime.now()


# a separate thread
__scheduler = BackgroundScheduler()
__jobs_info: List[JobInfo] = []


def __wrap_func(func: Callable, job_info: JobInfo):
    __jobs_info.insert(0, job_info)
    if len(__jobs_info) > MAX_SCHEDULE_JOB_INFO_LEN:
        # dequeue the oldest job
        __jobs_info.pop()

    @wraps(func)
    def wrapper(*args, **kwargs):
        job_info.execute_at = datetime.now()
        res = func(*args, **kwargs)
        job_info.finished_at = datetime.now()
        job_info.finished_return = res

    return wrapper


def get_jobs() -> List[JobInfo]:
    return __jobs_info


def clear_jobs() -> None:
    __jobs_info.clear()


def start():
    __scheduler.start()


def stop():
    __scheduler.shutdown()


def _get_default(args, kwargs):
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}
    return args, kwargs


def run_once_at(
        func: Callable,
        time: datetime,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
):
    args, kwargs = _get_default(args, kwargs)
    ji = JobInfo(
        type="date",
        args=args,
        kwargs=kwargs,
    )
    _func = __wrap_func(func=func, job_info=ji)
    __scheduler.add_job(
        func=_func,
        trigger="date",
        run_date=time,
        args=args,
        kwargs=kwargs,
    )


def run_once_now(
        func: Callable,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
):
    return run_once_at(func=func, time=datetime.now(), args=args, kwargs=kwargs)


def run_once_after(
        func: Callable,
        second: float,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
):
    return run_once_at(
        func=func,
        time=datetime.now() + timedelta(seconds=second),
        args=args,
        kwargs=kwargs,
    )


def run_every_at(
        func: Callable,
        second: Optional[int] = None,
        minute: Optional[int] = None,
        hour: Optional[int] = None,
        day: Optional[int] = None,
        month: Optional[int] = None,
        day_of_week: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
):
    args, kwargs = _get_default(args, kwargs)
    ji = JobInfo(
        type="cron",
        args=args,
        kwargs=kwargs,
    )
    _func = __wrap_func(func=func, job_info=ji)
    __scheduler.add_job(
        func=_func,
        trigger="cron",
        second=second,
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        start_date=start_date,
        end_date=end_date,
        args=args,
        kwargs=kwargs,
    )
