import multiprocessing
import shutil
import socket
import time
import unittest
from pathlib import Path

import requests

from rethink import run


class TestRun(unittest.TestCase):
    path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.path = p = Path(__file__).parent / "tmp"
        p.mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(str(cls.path), ignore_errors=True)

    def test_run(self):
        port = 8001
        p = multiprocessing.Process(target=run, kwargs={"path": self.path, "port": port, "language": "zh"})
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
            "/login",
            "/about",
            "/r",
            "/r/settings",
            "/r/user",
            "/r/import",
            "/n/123",
        ]:
            resp = requests.get(f"http://127.0.0.1:{port}{url}")
            self.assertEqual(200, resp.status_code, msg=f"failed to get {url}")
            self.assertEqual("text/html; charset=utf-8", resp.headers["content-type"])
            self.assertIn("Rethink", resp.text)

        p.kill()
        self.assertTrue(self.path.exists())
        self.assertTrue(self.path.is_dir())
        self.assertTrue((self.path / ".data").exists())
