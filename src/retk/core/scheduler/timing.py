from dataclasses import dataclass
from enum import Enum, auto


class Every(Enum):
    minute = 0
    hour = auto()
    day = auto()
    month = auto()


@dataclass
class Timing:
    at_second: int = 0
    at_minute: int = 0
    at_hour: int = 0
    at_day: int = 0
    every: Every = Every.hour


def __validate_time(day: int = None, hour: int = None, minute: int = None, second: int = None):
    if day is not None and (day >= 31 or day < 0):
        raise ValueError(f"Invalid day: {day}")
    if hour is not None and (hour >= 24 or hour < 0):
        raise ValueError(f"Invalid hour: {hour}")
    if minute is not None and (minute >= 60 or minute < 0):
        raise ValueError(f"Invalid minute: {minute}")
    if second is not None and (second >= 60 or second < 0):
        raise ValueError(f"Invalid second: {second}")


def every_minute_at(second: int = 0):
    __validate_time(second=second)
    return Timing(at_second=second, every=Every.minute)


def every_hour_at(minute: int, second: int = 0):
    __validate_time(minute=minute, second=second)
    return Timing(at_second=second, at_minute=minute, every=Every.hour)


def every_day_at(hour: int, minute: int = 0, second: int = 0):
    __validate_time(hour=hour, minute=minute, second=second)
    return Timing(at_second=second, at_minute=minute, at_hour=hour, every=Every.day)


def every_month_at(day: int, hour: int, minute: int = 0, second: int = 0):
    __validate_time(day=day, hour=hour, minute=minute, second=second)
    return Timing(at_second=second, at_minute=minute, at_hour=hour, at_day=day, every=Every.month)
