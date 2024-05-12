import time
import unittest
from datetime import datetime, timedelta

from retk.core import scheduler
from retk.logger import logger


class TestCoreAsyncTask(unittest.TestCase):
    def setUp(self) -> None:
        self.log_level = logger.level
        logger.setLevel("DEBUG")
        scheduler.start()

    def tearDown(self) -> None:
        logger.setLevel(self.log_level)
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
        time.sleep(1.1)
