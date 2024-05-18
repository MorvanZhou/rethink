import asyncio
import time
import unittest
from datetime import datetime, timedelta

from bson.tz_util import utc

from retk.const.settings import MAX_SCHEDULE_JOB_INFO_LEN
from retk.core import scheduler
from retk.logger import logger


def print_test(txt: str):
    text = f"test and print '{txt}'"
    print(text)
    return text


def fake_test(inp):
    return inp


def async_test(txt: str):
    async def async_test_inner(txt):
        text = f"async_test and print '{txt}'"
        print(text)
        return text

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(async_test_inner(txt))
    loop.close()
    return res


class TestCoreAsyncTask(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        scheduler.start()

    def setUp(self) -> None:
        scheduler.clear_jobs()
        self.log_level = logger.level
        logger.setLevel("DEBUG")

    def tearDown(self) -> None:
        logger.setLevel(self.log_level)

    @classmethod
    def tearDownClass(cls) -> None:
        scheduler.stop()

    def test_put_task(self):
        scheduler.run_once_after(
            job_id="test1",
            second=0,
            func=print_test,
            args=("1",),
        )
        scheduler.run_once_after(
            job_id="test2",
            func=print_test,
            second=0.001,
            args=("2",),
        )
        scheduler.run_once_at(
            job_id="test3",
            func=print_test,
            time=datetime.now(tz=utc),
            args=("3",),
        )
        scheduler.run_once_at(
            job_id="test4",
            func=print_test,
            time=datetime.now(tz=utc) + timedelta(seconds=0.003),
            args=("4",),
        )

        time.sleep(0.005)
        now = datetime.now(tz=utc)
        scheduler.run_every_at(
            job_id="test5",
            func=print_test,
            second=(now.second + 1) % 60,
            args=("5",),
        )

        self.assertEqual(5, len(scheduler.get_jobs()))
        for i, job in enumerate(scheduler.get_jobs()[::-1]):
            if i == 0:
                self.assertIsNone(job.finished_at, msg=job)
                continue
            fail = True
            for _ in range(10):
                if job.finished_at is None:
                    time.sleep(0.01)
                    continue
                self.assertIsInstance(job.finished_at, datetime)
                self.assertTrue(job.finished_return.startswith("test and print"))
                fail = False
            self.assertFalse(fail)

        time.sleep(1.1)

        for _, job in enumerate(scheduler.get_jobs()):
            self.assertIsInstance(job.finished_at, datetime)
            self.assertTrue(job.finished_return.startswith("test and print"))

        j = scheduler.get_job("test5")
        self.assertIsInstance(j, scheduler.schedule.JobInfo)
        self.assertEqual("test and print '5'", j.finished_return)

        with self.assertRaises(KeyError) as e:
            scheduler.run_once_now(
                job_id="test5",
                func=fake_test,
                args=(6,),
            )
            self.assertEqual("Job 'test5' already exists", str(e.exception))

    def test_async_task(self):
        scheduler.run_once_now(
            job_id="test1",
            func=async_test,
            args=("1",),
        )
        scheduler.run_once_now(
            job_id="test2",
            func=async_test,
            args=("2",),
        )
        self.assertEqual(2, len(scheduler.get_jobs()))
        for job in scheduler.get_jobs():
            fail = True
            for _ in range(10):
                if job.finished_at is None:
                    time.sleep(0.01)
                    continue
                self.assertIsInstance(job.finished_at, datetime)
                self.assertTrue(job.finished_return.startswith("async_test and print"))
                fail = False
            self.assertFalse(fail)

    def test_max_len(self):
        for i in range(MAX_SCHEDULE_JOB_INFO_LEN + 2):
            scheduler.run_once_now(
                job_id=f"test{i}",
                func=fake_test,
                args=(i,),
            )
        self.assertEqual(MAX_SCHEDULE_JOB_INFO_LEN, len(scheduler.get_jobs()))
        count = 2
        for j in scheduler.get_jobs():
            fail = True
            for _ in range(10):
                if j.finished_at is None:
                    time.sleep(0.01)
                    continue
                self.assertIsInstance(j.created_at, datetime)
                self.assertIsInstance(j.executed_at, datetime)
                self.assertGreaterEqual(j.executing_time(), timedelta(seconds=0))
                self.assertGreaterEqual(j.finished_at, j.executed_at)
                self.assertGreaterEqual(j.executed_at, j.created_at)
                self.assertEqual(count, j.finished_return, msg=str(j))
                fail = False
                break
            self.assertFalse(fail)
            count += 1
