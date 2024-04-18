import unittest

from retk.core import async_task
from retk.logger import logger


class TestCoreAsyncTask(unittest.TestCase):
    def setUp(self) -> None:
        self.log_level = logger.level
        logger.setLevel("DEBUG")
        async_task.init()

    def tearDown(self) -> None:
        logger.setLevel(self.log_level)

    def test_put_task(self):
        async_task.put_task(task_name=async_task.TaskName.TEST, x=1)
