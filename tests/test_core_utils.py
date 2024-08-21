import asyncio
import os
import shutil
import time
import unittest
import zipfile
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

import httpx

from retk.core.utils import md_tools
from retk.core.utils import ratelimiter
from retk.core.utils.cos import cos_client


def skip_no_cos(fn):
    async def wrapper(*args):
        if os.getenv("COS_BUCKET_NAME") is None:
            return
        return await fn(*args)

    return wrapper


class UtilsTest(unittest.IsolatedAsyncioTestCase):

    @patch("httpx.AsyncClient.get")
    async def test_single_rate_limiter(self, mock_get):
        mock_get.return_value = "mock"
        rate_limiter = ratelimiter.RateLimiter(requests=1, period=timedelta(seconds=0.1))
        st = time.time()
        count = 0

        async def fetch(url: str):
            nonlocal count
            async with rate_limiter:
                async with httpx.AsyncClient() as client:
                    await client.get(url)
                    count += 1

        n = 5
        tasks = [fetch("https://xxx") for _ in range(n)]
        await asyncio.gather(*tasks)
        total_time = time.time() - st
        self.assertGreaterEqual(total_time, 0.1 * (n - 1))
        # self.assertLess(total_time, 0.5)
        self.assertEqual(n, count)

    @patch("httpx.AsyncClient.get")
    async def test_rate_limiter(self, mock_get):
        mock_get.return_value = "mock"

        rate_limiter_1 = ratelimiter.RateLimiter(requests=15, period=timedelta(seconds=1))
        rate_limiter_2 = ratelimiter.RateLimiter(requests=5, period=timedelta(seconds=0.1))

        st = time.time()
        count = 0

        async def fetch(url: str):
            nonlocal count
            async with rate_limiter_1, rate_limiter_2:
                async with httpx.AsyncClient() as client:
                    await client.get(url)
                    count += 1

        tasks = [fetch("https://xxx") for _ in range(16)]
        await asyncio.gather(*tasks)
        total_time = time.time() - st
        self.assertGreaterEqual(total_time, 1)
        # self.assertLess(total_time, 2.5)
        self.assertEqual(16, count)

    async def test_concurrent_limiter(self):
        concurrent_limiter = ratelimiter.ConcurrentLimiter(n=2)
        st = time.time()
        count = 0

        async def fetch():
            nonlocal count
            async with concurrent_limiter:
                async with httpx.AsyncClient() as _:
                    await asyncio.sleep(0.1)
                    count += 1

        tasks = [fetch() for _ in range(5)]
        await asyncio.gather(*tasks)
        total_time = time.time() - st
        self.assertGreaterEqual(total_time, 0.29)
        # self.assertLess(total_time, 0.5)
        self.assertEqual(5, count)

    async def test_concurrent_with_rate_limiter(self):
        concurrent_limiter = ratelimiter.ConcurrentLimiter(n=2)
        rate_limiter = ratelimiter.RateLimiter(requests=3, period=timedelta(seconds=0.2))

        st = time.time()
        count = 0

        async def fetch():
            nonlocal count
            async with concurrent_limiter, rate_limiter:
                async with httpx.AsyncClient() as _:
                    await asyncio.sleep(0.1)
                    count += 1

        tasks = [fetch() for _ in range(4)]
        await asyncio.gather(*tasks)
        total_time = time.time() - st
        self.assertGreaterEqual(total_time, 0.29)
        # self.assertLess(total_time, 0.5)
        self.assertEqual(4, count)

    @skip_no_cos
    @patch("retk.config.is_local_db")
    def test_replace_app_files_in_md(self, mock_is_local_db):
        os.environ["RETHINK_LOCAL_STORAGE_PATH"] = "."
        os.environ["COS_DOMAIN"] = "cos.com"

        mock_is_local_db.return_value = True
        try:
            cos_client.init()
        except ModuleNotFoundError:
            return

        md = "[file](https://xxx) qdq ![img](/files/zzz) qdq\n [img](/files/yyy)\n![xx](/files/zzz)12"
        new_md, file_links = md_tools.replace_app_files_in_md("123", md)
        self.assertEqual(new_md, md)
        self.assertEqual(file_links, {"zzz", "yyy"})

        mock_is_local_db.return_value = False

        md = "[file](https://xxx) dqa ![img](https://cos.com/userData/123/zzz) dqa\n [img](https://cos.com/yyy)" \
             "\n![xx](https://cos.com/userData/123/aaa)12"
        new_md, file_links = md_tools.replace_app_files_in_md("123", md)
        self.assertEqual(file_links, {"zzz", "aaa"})
        self.assertEqual(new_md, "[file](https://xxx) dqa ![img](files/zzz) dqa\n [img](https://cos.com/yyy)"
                                 "\n![xx](files/aaa)12")

    @patch("retk.config.is_local_db")
    async def test_md2zipped_md_files(self, mock_is_local_db):
        os.environ["RETHINK_LOCAL_STORAGE_PATH"] = "temp"
        os.environ["COS_DOMAIN"] = "cos.com"
        mock_is_local_db.return_value = True
        os.makedirs(os.path.join("temp", ".data", "files"), exist_ok=True)

        md = "[file](https://xxx) qdq ![img](/files/zzz) qdq\n [img](/files/yyy)"
        with open(os.path.join("temp", "test.md"), "w") as f:
            f.write(md)
        with open(os.path.join("temp", ".data", "files", "zzz"), "w") as f:
            f.write("zzz")
        with open(os.path.join("temp", ".data", "files", "yyy"), "w") as f:
            f.write("yyy")

        media_type, buffer = await md_tools.md_export("123", "test", md, format_="md")
        self.assertEqual("application/zip", media_type)
        self.assertGreater(len(buffer.getvalue()), 0)

        with open(os.path.join("temp", "test.zip"), "wb") as f:
            f.write(buffer.getvalue())

        # unzip and check
        with zipfile.ZipFile(os.path.join("temp", "test.zip"), "r") as z:
            z.extractall("test_temp")
        with open(os.path.join("test_temp", "test.md"), "r") as f:
            new_md = f.read()
        self.assertEqual(md, new_md)
        with open(os.path.join("test_temp", "files", "zzz"), "r") as f:
            new_file = f.read()
        self.assertEqual("zzz", new_file)
        with open(os.path.join("test_temp", "files", "yyy"), "r") as f:
            new_file = f.read()
        self.assertEqual("yyy", new_file)

        shutil.rmtree("test_temp")
        shutil.rmtree("temp")

    @patch("retk.config.is_local_db")
    async def test_md2zipped_md_single_file(self, mock_is_local_db):
        os.environ["RETHINK_LOCAL_STORAGE_PATH"] = "temp"
        os.environ["COS_DOMAIN"] = "cos.com"
        mock_is_local_db.return_value = True

        md = "test"
        media_type, buffer = await md_tools.md_export("123", "test", md, format_="md")
        self.assertEqual("text/markdown", media_type)
        self.assertGreater(len(buffer.getvalue()), 0)

        md_ = buffer.getvalue().decode("utf-8")
        self.assertEqual(md, md_)

    @skip_no_cos
    async def test_async_get_cos_object(self):
        try:
            cos_client.init()
        except ModuleNotFoundError:
            return
        uid = os.getenv("UID", None)
        if uid is None:
            return
        filename = os.getenv("FILE", None)
        if filename is None:
            return

        os.makedirs("temp", exist_ok=True)
        data = await cos_client.async_get(uid=uid, filename=filename)
        with open(os.path.join("temp", "test.png"), "wb") as f:
            f.write(data)
        self.assertGreater(len(data), 0)
        # check if png file
        self.assertEqual(data[:4], b"\x89PNG")
        os.remove(os.path.join("temp", "test.png"))
        os.rmdir("temp")

    @skip_no_cos
    async def test_async_batch_get_cos(self):
        try:
            cos_client.init()
        except ModuleNotFoundError:
            return
        uid = os.getenv("UID", None)
        if uid is None:
            return
        filename1 = os.getenv("FILE1", None)
        if filename1 is None:
            return
        filename2 = os.getenv("FILE2", None)
        if filename2 is None:
            return

        os.makedirs("temp", exist_ok=True)
        data = await cos_client.async_batch_get(uid=uid, filenames=[filename1, filename2])
        for filename, data in data.items():
            with open(os.path.join("temp", filename), "wb") as f:
                f.write(data)
            self.assertGreater(len(data), 0)
            # check if png file
            self.assertEqual(data[:4], b"\x89PNG")
            os.remove(os.path.join("temp", filename))
        os.rmdir("temp")

    @skip_no_cos
    async def test_get_cos_object(self):
        try:
            cos_client.init()
        except ModuleNotFoundError:
            return
        uid = os.getenv("UID", None)
        if uid is None:
            return
        filename = os.getenv("FILE", None)
        if filename is None:
            return

        os.makedirs("temp", exist_ok=True)
        data = cos_client.get(uid=uid, filename=filename)
        with open(os.path.join("temp", "test.png"), "wb") as f:
            f.write(data)
        self.assertGreater(len(data), 0)
        # check if png file
        self.assertEqual(data[:4], b"\x89PNG")
        os.remove(os.path.join("temp", "test.png"))
        os.rmdir("temp")

    @skip_no_cos
    async def test_put_cos_object(self):
        try:
            cos_client.init()
        except ModuleNotFoundError:
            return
        uid = os.getenv("UID", None)
        if uid is None:
            return
        filename = "test.txt"

        file = BytesIO(b"test")
        os.makedirs("temp", exist_ok=True)
        ok = cos_client.put(file=file, uid=uid, filename=filename)
        self.assertTrue(ok)

        self.assertTrue(cos_client.has_file(uid=uid, filename=filename))

    @skip_no_cos
    async def test_async_put_cos_object(self):
        try:
            cos_client.init()
        except ModuleNotFoundError:
            return
        uid = os.getenv("UID", None)
        if uid is None:
            return
        filename = "test.txt"

        file = BytesIO(b"test")
        os.makedirs("temp", exist_ok=True)
        ok = await cos_client.async_put(file=file, uid=uid, filename=filename)
        self.assertTrue(ok)

        self.assertTrue(await cos_client.async_has_file(uid=uid, filename=filename))

    @skip_no_cos
    async def test_async_batch_put_cos(self):
        try:
            cos_client.init()
        except ModuleNotFoundError:
            return
        uid = os.getenv("UID", None)
        if uid is None:
            return
        files = {}
        for i in range(5):
            files[f"test_{i}.txt"] = BytesIO(b"test")

        res = await cos_client.async_batch_put(uid=uid, files=files)
        for v in res.values():
            self.assertTrue(v)

        self.assertTrue(await cos_client.async_batch_has_file(uid=uid, filenames=list(files.keys())))
