import json
from datetime import datetime
from pathlib import Path

from jinja2 import Template

import rethink


class DailySummary(rethink.Plugin):
    id = "dailySummary"
    name = "Daily Summary"
    version = "0.1.0"
    description = "summary my daily usage"
    author = "morvanzhou"
    icon = Path("_static") / "image" / "logo.svg"
    template = Template(
        (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
    )
    schedule_timing = rethink.schedule.every_day_at(hour=0, minute=0)

    def __init__(self):
        super().__init__()
        self.data_path = Path(__file__).parent / ".data.json"
        today = datetime.now().strftime("%Y-%m-%d")
        if not self.data_path.exists():
            self.data = [{
                "date": today,
                "word": 0,
                "node": 0,
            }]
            self.data_path.write_text(json.dumps(self.data))
        else:
            self.data = json.loads(self.data_path.read_text())
            if self.data[0]["date"] != today:
                self.data.insert(0, {
                    "date": today,
                    "word": 0,
                    "node": 0,
                })
                self.data = self.data[:120]
                self.write_to_file()

    def on_node_updated(self, node: rethink.tps.Node, old_md: str) -> None:
        self.data[0]["word"] += len(node["md"]) - len(old_md)
        self.write_to_file()

    def on_node_added(self, node: rethink.tps.Node) -> None:
        self.data[0]["word"] += len(node["md"])
        self.data[0]["node"] += 1
        self.write_to_file()

    def on_schedule(self):
        self.data.insert(0, {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "word": 0,
            "node": 0,
        })
        self.data = self.data[:120]
        self.write_to_file()

    def render(self):
        d = self.data[:7]
        return self.template.render(
            name=self.name,
            data=d,
        )

    def write_to_file(self):
        self.data_path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
