from datetime import datetime, timedelta
from typing import Callable, Optional, Tuple, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler

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

# a separate thread
_scheduler = BackgroundScheduler()


def start():
    _scheduler.start()


def stop():
    _scheduler.shutdown()


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
    _scheduler.add_job(
        func=func,
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
    _scheduler.add_job(
        func=func,
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
