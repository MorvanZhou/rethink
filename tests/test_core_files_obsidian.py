import io
import os
import unittest
from textwrap import dedent
from zipfile import ZipFile, BadZipFile

from bson import ObjectId

from retk import core, const
from retk.core.files import saver
from retk.core.files.importing.async_tasks.obsidian import ops
from retk.models.client import client
from . import utils


class ObsidianTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")
        cls.orig_folder_data = {
            os.path.join("a", "test.md"): b"hello world",
            os.path.join("a", "a.md"): b"a",
            os.path.join("a", "v", "q文档.md"): "阿斯顿请问".encode("utf-8"),
        }
        cls.orig_data = {
            "test.md": b"hello world",
            "a.md": b"a",
            "q文档.md": "阿斯顿请问".encode("utf-8"),
        }

    async def asyncSetUp(self) -> None:
        await client.init()
        u, _ = await core.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.uid = u["id"]

    async def asyncTearDown(self) -> None:
        await client.drop()

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    def test_unzip_folder(self):
        zip_bytes = ZipFile("test.zip", "w")
        for k, v in self.orig_folder_data.items():
            zip_bytes.writestr(k, v)
        zip_bytes.close()

        # unzip
        with open("test.zip", "rb") as f:
            extracted_files = ops.unzip_obsidian(f.read())
        for full_path, meta in extracted_files.md_full.items():
            self.assertEqual(full_path, meta.filepath)
            self.assertEqual(
                self.orig_folder_data[os.path.join("a", full_path)],
                meta.file,
                msg=str(self.orig_folder_data))
        for filename, meta in extracted_files.md.items():
            self.assertEqual(
                self.orig_data[filename],
                meta.file,
                msg=filename)
        os.remove("test.zip")

    def test_unzip_files(self):
        zip_bytes = ZipFile("test.zip", "w")
        for k, v in self.orig_data.items():
            zip_bytes.writestr(k, v)
        zip_bytes.close()

        # unzip
        with open("test.zip", "rb") as f:
            extracted_files = ops.unzip_obsidian(f.read())
        for filename, meta in extracted_files.md.items():
            self.assertEqual(
                self.orig_data[filename],
                meta.file,
                msg=filename)
        os.remove("test.zip")

    def test_unzip_not_zip(self):
        with open("test.zip", "wb") as f:
            f.write(b"hello world")
        with open("test.zip", "rb") as f:
            with self.assertRaises(BadZipFile):
                _ = ops.unzip_obsidian(f.read())
        os.remove("test.zip")

    def test_file_hash(self):
        for h, b in [
            ("d41d8cd98f00b204e9800998ecf8427e", b""),
            ("9e107d9d372bb6826bd81d3542a419d6", b"The quick brown fox jumps over the lazy dog")
        ]:
            file = saver.File(
                data=io.BytesIO(b),
                filename="aa.md",
            )
            self.assertEqual(".md", file.ext)
            self.assertEqual(const.app.FileTypesEnum.PLAIN, file.type)
            self.assertEqual(h + ".md", file.hashed_filename)

    async def test_replace_inner_link(self):
        md = dedent("""\
            # 123
            ddd qwd [[123]] 345
            [[我哦]]
            """)
        o1 = str(ObjectId())
        o2 = str(ObjectId())
        exist_path2nid = {"123.md": o1, "我哦.md": o2}
        res = await ops.replace_inner_link_and_upload(
            uid="",
            md=md,
            exist_path2nid=exist_path2nid,
            others_full={},
            others_name={},
        )
        self.assertEqual(dedent(f"""\
            # 123
            ddd qwd [@123](/n/{o1}) 345
            [@我哦](/n/{o2})
            """), res)
        self.assertEqual({"123.md": o1, "我哦.md": o2}, exist_path2nid)

    async def test_replace_inner_link_new(self):
        md = dedent("""\
            # 123
            ddd qwd [[123]] 345
            [[我哦]]
            """)

        o1 = str(ObjectId())
        exist_path2nid = {"123.md": o1}
        res = await ops.replace_inner_link_and_upload(
            uid="",
            md=md,
            exist_path2nid=exist_path2nid,
            others_full={},
            others_name={},
        )
        self.assertEqual(dedent(f"""\
            # 123
            ddd qwd [@123](/n/{o1}) 345
            [@我哦](/n/{exist_path2nid['我哦.md']})
            """), res)
        self.assertIn("我哦.md", exist_path2nid)
