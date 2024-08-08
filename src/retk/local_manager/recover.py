import json
import os
from pathlib import Path
from typing import Dict, Optional, TypedDict

from bson import ObjectId

from retk import const, utils, config
from retk._version import __version__


class DotRethinkSettingsLLMApi(TypedDict):
    service: str
    model: str
    auth: Dict[str, str]


class DotRethinkSettings(TypedDict):
    language: str
    theme: str
    editorMode: str
    editorFontSize: int
    editorCodeTheme: str
    editorSepRightWidth: int
    editorSideCurrentToolId: str
    llmApi: Optional[DotRethinkSettingsLLMApi]


class DotRethink(TypedDict):
    version: str
    _id: ObjectId
    id: str
    email: str
    nickname: str
    avatar: str
    account: str
    settings: DotRethinkSettings


def dump_default_dot_rethink() -> DotRethink:
    path = get_dot_rethink_path()
    version = DotRethink(
        version=__version__,
        _id=ObjectId(),
        id=utils.short_uuid(),
        email=const.DEFAULT_USER["email"],
        nickname=const.DEFAULT_USER["nickname"],
        avatar=const.DEFAULT_USER["avatar"],
        account=const.DEFAULT_USER["email"],
        settings=DotRethinkSettings(
            language=os.getenv("RETHINK_DEFAULT_LANGUAGE", const.LanguageEnum.EN.value),
            theme=const.app.AppThemeEnum.LIGHT.value,
            editorMode=const.app.EditorModeEnum.WYSIWYG.value,
            editorFontSize=15,
            editorCodeTheme=const.app.EditorCodeThemeEnum.GITHUB.value,
            editorSepRightWidth=200,
            editorSideCurrentToolId="",
            llmApi=None,
        )
    )
    with open(path, "w", encoding="utf-8") as f:
        out = version.copy()
        out["_id"] = str(out["_id"])
        json.dump(out, f, indent=2, ensure_ascii=False)
    return version


def load_dot_rethink() -> Optional[DotRethink]:
    path = get_dot_rethink_path()
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_dot_rethink_path() -> Path:
    return config.get_settings().RETHINK_LOCAL_STORAGE_PATH / const.settings.DOT_DATA / ".rethink.json"
