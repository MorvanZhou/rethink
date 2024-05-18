from collections import OrderedDict as _OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Optional, Tuple, Dict, Any, List, OrderedDict

from apscheduler.schedulers.background import BackgroundScheduler
from bson.tz_util import utc

from retk import const
from retk.const.settings import MAX_SCHEDULE_JOB_INFO_LEN
from . import tasks

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
    id: str
    type: str
    args: Tuple
    kwargs: Dict[str, Any]
    executed_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    finished_return: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        self.created_at = datetime.now(tz=utc)

    def executing_time(self) -> timedelta:
        if self.executed_at is None:
            return timedelta(seconds=0)
        if self.finished_at is None:
            return datetime.now() - self.executed_at
        return self.finished_at - self.executed_at

    def is_failed(self) -> bool:
        return self.finished_at is not None and self.executed_at is None


# a separate thread
__scheduler: Optional[BackgroundScheduler] = None
__jobs_info: OrderedDict[str, JobInfo] = _OrderedDict()


def __wrap_func(func: Callable, job_info: JobInfo) -> Optional[Callable]:
    if job_info.id in __jobs_info or __scheduler.get_job(job_info.id) is not None:
        raise KeyError(f"job id {job_info.id} already exists")

    __jobs_info[job_info.id] = job_info
    if len(__jobs_info) > MAX_SCHEDULE_JOB_INFO_LEN:
        # dequeue the oldest job
        __jobs_info.popitem(last=False)

    @wraps(func)
    def wrapper(*args, **kwargs):
        job_info.executed_at = datetime.now(tz=utc)
        res = func(*args, **kwargs)
        job_info.finished_at = datetime.now(tz=utc)
        job_info.finished_return = res

    return wrapper


def init_tasks():
    # check unscheduled system notices every minute
    run_every_at(
        job_id="deliver_unscheduled_system_notices",
        func=tasks.notice.deliver_unscheduled_system_notices,
        second=0,
    )
    return


def get_jobs() -> List[JobInfo]:
    # from oldest to newest
    return list(__jobs_info.values())


def get_job(job_id: str) -> Optional[JobInfo]:
    return __jobs_info.get(job_id)


def clear_jobs() -> None:
    __jobs_info.clear()


def start():
    global __scheduler
    __scheduler = BackgroundScheduler()
    __scheduler.start()


def stop():
    __scheduler.remove_all_jobs()
    __scheduler.shutdown()


def _get_default(args, kwargs):
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}
    return args, kwargs


def run_once_at(
        job_id: str,
        func: Callable,
        time: datetime,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
) -> Tuple[JobInfo, const.CodeEnum]:
    args, kwargs = _get_default(args, kwargs)
    ji = JobInfo(
        id=job_id,
        type="date",
        args=args,
        kwargs=kwargs,
    )
    _func = __wrap_func(func=func, job_info=ji)
    if _func is None:
        return ji, const.CodeEnum.INVALID_SCHEDULE_JOB_ID
    __scheduler.add_job(
        id=job_id,
        func=_func,
        trigger="date",
        run_date=time,
        args=args,
        kwargs=kwargs,
    )
    return ji, const.CodeEnum.OK


def run_once_now(
        job_id: str,
        func: Callable,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
) -> Tuple[JobInfo, const.CodeEnum]:
    return run_once_at(job_id=job_id, func=func, time=datetime.now(tz=utc), args=args, kwargs=kwargs)


def run_once_after(
        job_id: str,
        func: Callable,
        second: float,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
) -> Tuple[JobInfo, const.CodeEnum]:
    return run_once_at(
        job_id=job_id,
        func=func,
        time=datetime.now(tz=utc) + timedelta(seconds=second),
        args=args,
        kwargs=kwargs,
    )


def run_every_at(
        job_id: str,
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
) -> Tuple[JobInfo, const.CodeEnum]:
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
        id=job_id,
        type="cron",
        args=args,
        kwargs=kwargs,
    )
    _func = __wrap_func(func=func, job_info=ji)
    if _func is None:
        return ji, const.CodeEnum.INVALID_SCHEDULE_JOB_ID
    __scheduler.add_job(
        id=job_id,
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
    return ji, const.CodeEnum.OK
