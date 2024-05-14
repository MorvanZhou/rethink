import time
import unittest
from datetime import datetime, timedelta

from retk.const.settings import MAX_SCHEDULE_JOB_INFO_LEN
from retk.core import scheduler
from retk.logger import logger


class TestCoreAsyncTask(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        scheduler.start()

    def setUp(self) -> None:
        self.log_level = logger.level
        logger.setLevel("DEBUG")

    def tearDown(self) -> None:
        logger.setLevel(self.log_level)
        scheduler.clear_jobs()

    @classmethod
    def tearDownClass(cls) -> None:
        scheduler.stop()

    def test_put_task(self):
        scheduler.run_once_after(
            second=0,
            func=scheduler.tasks.test.print_test,
            args=("1",),
        )
        scheduler.run_once_after(
            func=scheduler.tasks.test.print_test,
            second=0.001,
            args=("2",),
        )
        scheduler.run_once_at(
            func=scheduler.tasks.test.print_test,
            time=datetime.now(),
            args=("3",),
        )
        scheduler.run_once_at(
            func=scheduler.tasks.test.print_test,
            time=datetime.now() + timedelta(seconds=0.003),
            args=("4",),
        )

        time.sleep(0.005)
        now = datetime.now()
        scheduler.run_every_at(
            func=scheduler.tasks.test.print_test,
            second=now.second + 1 % 60,
            args=("5",),
        )

        self.assertEqual(5, len(scheduler.get_jobs()))
        for i, job in enumerate(scheduler.get_jobs()):
            if i == 0:
                self.assertIsNone(job.finished_at)
            else:
                self.assertIsInstance(job.finished_at, datetime)
                self.assertTrue(job.finished_return.startswith("test and print"))

        time.sleep(1.01)

        for i, job in enumerate(scheduler.get_jobs()):
            self.assertIsInstance(job.finished_at, datetime)
            self.assertTrue(job.finished_return.startswith("test and print"))

    def test_max_len(self):
        for i in range(MAX_SCHEDULE_JOB_INFO_LEN + 2):
            scheduler.run_once_now(
                func=scheduler.tasks.test.fake_test,
                args=(i,),
            )
        self.assertEqual(MAX_SCHEDULE_JOB_INFO_LEN, len(scheduler.get_jobs()))
        count = 2
        for j in scheduler.get_jobs()[::-1]:
            fail = True
            for _ in range(10):
                if j.finished_at is None:
                    time.sleep(0.01)
                    continue
                self.assertIsInstance(j.created_at, datetime)
                self.assertIsInstance(j.execute_at, datetime)
                self.assertGreaterEqual(j.executing_time(), timedelta(seconds=0))
                self.assertGreaterEqual(j.finished_at, j.execute_at)
                self.assertGreaterEqual(j.execute_at, j.created_at)
                self.assertEqual(count, j.finished_return, msg=str(j))
                fail = False
                break
            self.assertFalse(fail)
            count += 1
