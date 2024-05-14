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

    def executing_time(self) -> timedelta:
        if self.finished_at is None:
            return datetime.now() - self.execute_at
        return self.finished_at - self.execute_at


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
        week: Optional[int] = None,
        month: Optional[int] = None,
        day_of_week: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
):
    if second is not None:
        second = int(second)
        if second > 59 or second < 0:
            raise ValueError("second must be in range 0-59")
    if minute is not None:
        minute = int(minute)
        if minute > 59 or minute < 0:
            raise ValueError("minute must be in range 0-59")
    if hour is not None:
        hour = int(hour)
        if hour > 23 or hour < 0:
            raise ValueError("hour must be in range 0-23")
    if day is not None:
        day = int(day)
        if day > 31 or day < 1:
            raise ValueError("day must be in range 1-31")
    if week is not None:
        week = int(week)
        if week > 53 or week < 1:
            raise ValueError("week must be in range 1-53")
    if month is not None:
        month = int(month)
        if month > 12 or month < 1:
            raise ValueError("month must be in range 1-12")
    if day_of_week is not None:
        day_of_week = int(day_of_week)
        if day_of_week > 6 or day_of_week < 0:
            raise ValueError("day_of_week must be in range 0-6")

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
