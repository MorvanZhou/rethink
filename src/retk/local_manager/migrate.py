import json
from typing import Dict, Optional

from retk import const
from retk._version import __version__
from retk.local_manager.recover import get_dot_rethink_path
from retk.logger import logger


def version_tuple(v):
    return tuple(map(int, (v.split("."))))


__current_version = version_tuple(__version__)


def __version_less_than(dot_rethink: Dict, version) -> bool:
    dot_version = dot_rethink.get("version")
    if dot_version is None:
        return True
    return version_tuple(dot_version) < version_tuple(version)


def __migrate_older_to_0_2_9(dot_rethink: Dict) -> Dict:
    """Migrate the database to version 0.2.8.
    """
    v = "0.2.9"
    dot_rethink["version"] = v
    if "settings" not in dot_rethink:
        dot_rethink["settings"] = {
            "language": const.LanguageEnum.EN.value,
            "theme": const.app.AppThemeEnum.LIGHT.value,
            "editorMode": const.app.EditorModeEnum.WYSIWYG.value,
            "editorFontSize": 15,
            "editorCodeTheme": const.app.EditorCodeThemeEnum.GITHUB.value,
            "editorSepRightWidth": 200,
            "editorSideCurrentToolId": "",
        }
        logger.debug(f"Migrate the database to version {v}")
    __renew_dot_rethink(dot_rethink)
    return dot_rethink


def __migrate_older_to_0_3_0(dot_rethink: Dict) -> Dict:
    """Migrate the database to version 0.3.0.
    """
    v = "0.3.0"
    dot_rethink = __migrate_older_to_0_2_9(dot_rethink)
    if "llmApi" not in dot_rethink["settings"]:
        dot_rethink["settings"]["llmApi"] = {}
        logger.debug(f"Migrate the database to version {v}")
    __renew_dot_rethink(dot_rethink)
    return dot_rethink


def __read_dot_rethink() -> Optional[Dict]:
    """Read the .rethink file.

    Returns:
        Dict: the content of the .rethink file.
    """

    try:
        with open(get_dot_rethink_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def __renew_dot_rethink(dot_rethink: Dict):
    """Rewrite the .rethink file.

    Args:
        dot_rethink (Dict): the content of the .rethink file.
    """
    with open(get_dot_rethink_path(), "w", encoding="utf-8") as f:
        json.dump(dot_rethink, f, indent=2, ensure_ascii=False)


def to_latest_version():
    """Migrate the database to the latest version.
    """
    dot_rethink = __read_dot_rethink()
    if dot_rethink is None:
        logger.debug(".rethink.json is not found. The database is empty.")
        return

    if __version_less_than(dot_rethink, version="0.3.0"):
        __migrate_older_to_0_3_0(dot_rethink)
        return
