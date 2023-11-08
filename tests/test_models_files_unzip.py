import os
import unittest
from zipfile import ZipFile, BadZipFile

from rethink.models.files import unzip


class UnzipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.orig_folder_data = {
            os.path.join("a", "test.txt"): b"hello world",
            os.path.join("a", "a.txt"): b"a",
            os.path.join("a", "v", "q文档.txt"): "阿斯顿请问".encode("utf-8"),
        }
        cls.orig_data = {
            "test.txt": b"hello world",
            "a.txt": b"a",
            "q文档.txt": "阿斯顿请问".encode("utf-8"),
        }

    def test_unzip_folder(self):
        zip_bytes = ZipFile("test.zip", "w")
        for k, v in self.orig_folder_data.items():
            zip_bytes.writestr(k, v)
        zip_bytes.close()

        # unzip
        with open("test.zip", "rb") as f:
            extracted_files = unzip.unzip_file(f.read())
        for filename, data in extracted_files.items():
            self.assertEqual(
                self.orig_folder_data[os.path.join("a", *filename.split("/"))],
                data["file"],
                msg=str(self.orig_folder_data))
        os.remove("test.zip")

    def test_unzip_files(self):
        zip_bytes = ZipFile("test.zip", "w")
        for k, v in self.orig_data.items():
            zip_bytes.writestr(k, v)
        zip_bytes.close()

        # unzip
        with open("test.zip", "rb") as f:
            extracted_files = unzip.unzip_file(f.read())
        for filename, data in extracted_files.items():
            self.assertEqual(self.orig_data[filename], data["file"])
        os.remove("test.zip")

    def test_unzip_not_zip(self):
        with open("test.zip", "wb") as f:
            f.write(b"hello world")
        with open("test.zip", "rb") as f:
            with self.assertRaises(BadZipFile):
                _ = unzip.unzip_file(f.read())
        os.remove("test.zip")
