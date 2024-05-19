import json
from pathlib import Path
from typing import Union, Dict, Optional

from retk import const
from retk._version import __version__
from retk.logger import logger


def version_tuple(v):
    return tuple(map(int, (v.split("."))))


__current_version = version_tuple(__version__)


def __version_less_than(dot_rethink: Dict, version) -> bool:
    dot_version = dot_rethink.get("version")
    if dot_version is None:
        return True
    return version_tuple(dot_version) < version_tuple(version)


def __migrate_older_to_0_2_8(dot_rethink: Dict, data_path: Path):
    """Migrate the database to version 0.2.8.

    Args:
        data_path (str): the path to the database folder.
    """
    v = "0.2.8"
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
    __renew_dot_rethink(dot_rethink, data_path)
    logger.debug(f"Migrate the database to version {v}")


def __read_dot_rethink(data_path: Path) -> Optional[Dict]:
    """Read the .rethink file.

    Args:
        data_path (str): the path to the database folder.

    Returns:
        Dict: the content of the .rethink file.
    """
    dot_rethink = data_path / const.settings.DOT_DATA / ".rethink.json"
    try:
        with open(dot_rethink, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def __renew_dot_rethink(dot_rethink: Dict, data_path: Path):
    """Rewrite the .rethink file.

    Args:
        dot_rethink (Dict): the content of the .rethink file.
        data_path (str): the path to the database folder.
    """
    with open(data_path / const.settings.DOT_DATA / ".rethink.json", "w", encoding="utf-8") as f:
        json.dump(dot_rethink, f, indent=2, ensure_ascii=False)


def to_latest_version(data_path: Union[str, Path] = "."):
    """Migrate the database to the latest version.

    Args:
        data_path (str): the path to the database folder.
    """
    if not isinstance(data_path, Path):
        data_path = Path(data_path)
    dot_rethink = __read_dot_rethink(data_path)
    if dot_rethink is None:
        logger.debug(".rethink.json is not found. The database is empty.")
        return

    if __version_less_than(dot_rethink, version="0.2.8"):
        __migrate_older_to_0_2_8(dot_rethink, data_path)
        return
