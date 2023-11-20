import io
import os
import unittest
from textwrap import dedent
from zipfile import ZipFile, BadZipFile

from bson import ObjectId

from rethink import config
from rethink.models.files import file_ops


class UnzipTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config.get_settings.cache_clear()
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

    @classmethod
    def tearDownClass(cls) -> None:
        config.get_settings.cache_clear()

    def test_unzip_folder(self):
        zip_bytes = ZipFile("test.zip", "w")
        for k, v in self.orig_folder_data.items():
            zip_bytes.writestr(k, v)
        zip_bytes.close()

        # unzip
        with open("test.zip", "rb") as f:
            extracted_files = file_ops.unzip_file(f.read())
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
            extracted_files = file_ops.unzip_file(f.read())
        for filename, data in extracted_files.items():
            self.assertEqual(self.orig_data[filename], data["file"])
        os.remove("test.zip")

    def test_unzip_not_zip(self):
        with open("test.zip", "wb") as f:
            f.write(b"hello world")
        with open("test.zip", "rb") as f:
            with self.assertRaises(BadZipFile):
                _ = file_ops.unzip_file(f.read())
        os.remove("test.zip")

    def test_file_hash(self):
        self.assertEqual(
            "d41d8cd98f00b204e9800998ecf8427e",
            file_ops.file_hash(io.BytesIO(b"")))
        bio = io.BytesIO(b"The quick brown fox jumps over the lazy dog")
        self.assertEqual(
            "9e107d9d372bb6826bd81d3542a419d6",
            file_ops.file_hash(bio))

        self.assertEqual(b"The quick brown fox jumps over the lazy dog", bio.read())

    async def test_replace_inner_link(self):
        md = dedent("""\
            # 123
            ddd qwd [[123]] 345
            [[我哦]]
            """)
        o1 = str(ObjectId())
        o2 = str(ObjectId())
        filename2nid = {"123": o1, "我哦": o2}
        res = await file_ops.replace_inner_link_and_upload_image(
            uid="",
            md=md,
            exist_filename2nid=filename2nid,
            img_path_dict={},
            img_name_dict={},
            resize_threshold=0,
        )
        self.assertEqual(dedent(f"""\
            # 123
            ddd qwd [@123](/n/{o1}) 345
            [@我哦](/n/{o2})
            """), res)
        self.assertEqual({"123": o1, "我哦": o2}, filename2nid)

    async def test_replace_inner_link_new(self):
        md = dedent("""\
            # 123
            ddd qwd [[123]] 345
            [[我哦]]
            """)

        o1 = str(ObjectId())
        filename2nid = {"123": o1}
        res = await file_ops.replace_inner_link_and_upload_image(
            uid="",
            md=md,
            exist_filename2nid=filename2nid,
            img_path_dict={},
            img_name_dict={},
            resize_threshold=0,
        )
        self.assertEqual(dedent(f"""\
            # 123
            ddd qwd [@123](/n/{o1}) 345
            [@我哦](/n/{filename2nid['我哦']})
            """), res)
        self.assertIn("我哦", filename2nid)
