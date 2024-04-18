import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Template

import retk


class Favorites(retk.Plugin):
    id = "favorites"
    name = "Favorites"
    version = "0.1.0"
    description = "favorites thoughts"
    author = "morvanzhou"
    icon = Path("_static") / "logo.svg"

    def __init__(self):
        super().__init__()
        self.data_path = Path(__file__).parent / ".data.json"
        if not self.data_path.exists():
            self.data = OrderedDict()
            self.data_path.write_text(json.dumps(self.data))
        else:
            self.data = OrderedDict(json.loads(self.data_path.read_text()))

        self.template_home = Template(
            (Path(__file__).parent / "templates" / "home.html").read_text(encoding="utf-8")
        )
        self.template_side = Template(
            (Path(__file__).parent / "templates" / "side.html").read_text(encoding="utf-8")
        )

    def render_plugin_home(self, language: str) -> str:
        return self.template_home.render(
            add_btn_name="Add to Favorites" if language == "en" else "添加到收藏夹",
            h1=self.name,
            items=list(self.data.values()),
            plugin_id=self.id,
            call_url=self.api_call_url,
        )

    def render_editor_side(self, uid: str, nid: str, md: str, language: str) -> str:
        return self.template_side.render(
            add_btn_name="Add to Favorites" if language == "en" else "添加到收藏夹",
            h1=self.name,
            items=list(self.data.values()),
            nid=nid,
            title=md.strip().split("\n", 1)[0],
            plugin_id=self.id,
            call_url=self.api_call_url,
        )

    def handle_api_call(self, method: str, data: Any) -> retk.PluginAPICallReturn:
        if method == "add":
            if data["nid"] in self.data:
                return retk.PluginAPICallReturn(
                    success=False,
                    message=f"nid='{data['nid']}' already in favorites",
                    data=None
                )
            self.update_file(add=data)
        elif method == "remove":
            if data["nid"] not in self.data:
                return retk.PluginAPICallReturn(
                    success=False,
                    message=f"nid='{data['nid']}' not in favorites",
                    data=None
                )
            self.update_file(remove_nid=data["nid"])
        else:
            return retk.PluginAPICallReturn(
                success=False,
                message=f"method='{method}' is not allowed",
                data=None
            )
        return retk.PluginAPICallReturn(
            success=True,
            message="success",
            data=None
        )

    def update_file(self, add: dict = None, remove_nid: str = None):
        if add is not None:
            add["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.data[add["nid"]] = add
        if remove_nid is not None:
            self.data.pop(remove_nid)
        self.data_path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
