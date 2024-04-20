import unittest

from retk.run import _test_run


class TestRun(unittest.TestCase):
    def test_run(self):
        _test_run()

    # def test_plugin(self):
    #
    #     class TestPlugin(retk.Plugin):
    #         name = "TestPlugin"
    #         version = "0.1.0"
    #         description = "A demo test plugin."
    #         author = "morvanzhou"
    #         template = "<h1>{h}</h1>\n<p>{p}</p>"
    #         schedule_timing = retk.schedule.every_minute_at(second=0)
    #
    #         def __init__(self):
    #             super().__init__()
    #             self.count = 0
    #
    #         def on_schedule(self) -> None:
    #             print(self.count, time.time())
    #             self.count += 1
    #
    #     plugin = TestPlugin()
    #     retk.add_plugin(plugin)
    #     retk.run()
