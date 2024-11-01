import json
import shutil
import unittest
from pathlib import Path

from retk import const, config, local_manager, __version__
from retk.local_manager import recover
from tests import utils


class RecoverTest(unittest.TestCase):
    def setUp(self) -> None:
        utils.set_env(".env.test.local")
        self.tmp_dir = Path(__file__).parent / "temp"
        (self.tmp_dir / ".data").mkdir(parents=True, exist_ok=True)
        config.get_settings().RETHINK_LOCAL_STORAGE_PATH = self.tmp_dir

    def tearDown(self) -> None:
        # remove all files and dirs
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_package_version(self):
        vs = __version__.split(".")
        vs_int = list(map(int, vs))
        self.assertEqual(3, len(vs_int))

    def test_dump_load(self):
        local_manager.recover.dump_default_dot_rethink()

        v = local_manager.recover.load_dot_rethink()
        self.assertIsNotNone(v)
        # self.assertEqual(__version__, v["version"])
        self.assertEqual(const.DEFAULT_USER["email"], v["email"])
        self.assertEqual(const.DEFAULT_USER["nickname"], v["nickname"])
        self.assertEqual(const.DEFAULT_USER["avatar"], v["avatar"])
        self.assertEqual(const.DEFAULT_USER["email"], v["account"])
        self.assertEqual(const.LanguageEnum.EN.value, v["settings"]["language"])
        self.assertEqual(const.app.AppThemeEnum.LIGHT.value, v["settings"]["theme"])
        self.assertEqual(const.app.EditorModeEnum.WYSIWYG.value, v["settings"]["editorMode"])
        self.assertEqual(15, v["settings"]["editorFontSize"])
        self.assertEqual(const.app.EditorCodeThemeEnum.GITHUB.value, v["settings"]["editorCodeTheme"])
        self.assertEqual(200, v["settings"]["editorSepRightWidth"])
        self.assertEqual("", v["settings"]["editorSideCurrentToolId"])


class MigrateTest(unittest.TestCase):
    def setUp(self) -> None:
        utils.set_env(".env.test.local")
        self.tmp_dir = Path(__file__).parent / "temp"
        (self.tmp_dir / ".data").mkdir(parents=True, exist_ok=True)
        config.get_settings().RETHINK_LOCAL_STORAGE_PATH = self.tmp_dir

    def tearDown(self) -> None:
        # remove all files and dirs
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_merge_to_0_2_7(self):
        dot_rethink = {
            "_id": "65658d61dc7f58455d9b38b6",
            "id": "a" * 22,
            "email": "test@rethink.run",
            "nickname": "rethink",
            "avatar": "",
            "account": "test@rethink.run",
            "language": "en"
        }

        dot_data_dir = self.tmp_dir / const.settings.DOT_DATA
        dot_data_dir.mkdir(parents=True, exist_ok=True)

        with open(recover.get_dot_rethink_path(), "w", encoding="utf-8") as f:
            json.dump(dot_rethink, f, indent=2, ensure_ascii=False)
        local_manager.migrate.to_latest_version()
        v = local_manager.recover.load_dot_rethink()
        # self.assertEqual(__version__, v["version"])
        self.assertGreater(len(v["version"]), 0)
        self.assertIn("settings", v)
