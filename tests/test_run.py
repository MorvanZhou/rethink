import multiprocessing
import shutil
import socket
import time
import unittest
import urllib.request
from pathlib import Path

import retk
from retk import config, const


class TestRun(unittest.TestCase):
    path: Path

    @classmethod
    def setUpClass(cls) -> None:
        config.get_settings.cache_clear()
        cls.path = p = Path(__file__).parent / "tmp"
        p.mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(str(cls.path), ignore_errors=True)
        config.get_settings.cache_clear()

    def test_run(self, password=None):
        port = 8001

        p = multiprocessing.Process(target=retk.run, kwargs={
            "path": self.path, "port": port, "language": "zh", "headless": True,
            "debug": True, "password": password,
        })
        p.start()
        # p.join()
        while True:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                break
            time.sleep(0.1)

        for url in [
            "",
            "/r",
            "/r/login",
            "/r/sauth",
            "/r/settings",
            "/r/user",
            "/r/import",
            "/r/n/123",
        ]:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}{url}")
            self.assertEqual(200, resp.status, msg=f"failed to get {url}")
            self.assertEqual("text/html; charset=utf-8", resp.headers["content-type"])
            html = resp.read().decode()
            self.assertIn("Rethink", html)
            self.assertIn('<div id="app">', html)

        p.kill()
        p.join()
        self.assertTrue(self.path.exists())
        self.assertTrue(self.path.is_dir())
        self.assertTrue((self.path / ".data").exists())
        self.assertEqual(2, len(list((self.path / const.settings.DOT_DATA / "md").glob("*.md"))))

    def test_run_with_pw(self):
        return self.test_run(password="12345678")

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
