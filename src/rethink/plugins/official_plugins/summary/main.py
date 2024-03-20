from jinja2 import Template

import rethink


class DailySummary(rethink.Plugin):
    id = "dailySummary"
    name = "Daily Summary"
    version = "0.1.0"
    description = "summary my daily usage"
    author = "morvanzhou"
    template = Template(
        f"<h1>{name}</h1>"
        f"<p>today new thoughts: {{{{ node_count }}}}</p>"
        f"<p>today word count: {{{{ word_count }}}}</p>"
        f"<p>last day thoughts: {{{{ last_node_count }}}}</p>"
        f"<p>last day word count: {{{{ last_word_count }}}}</p>"
    )
    schedule_timing = rethink.schedule.every_day_at(hour=0, minute=0)

    def __init__(self):
        super().__init__()
        self.today_node_count = 0
        self.today_word_count = 0
        self.last_day_node_count = 0
        self.last_day_word_count = 0

    def on_node_updated(self, node: rethink.tps.Node, old_md: str) -> None:
        self.today_word_count += len(node["md"]) - len(old_md)

    def on_node_added(self, node: rethink.tps.Node) -> None:
        self.today_word_count += len(node["md"])
        self.today_node_count += 1

    def on_schedule(self):
        self.last_day_word_count = self.today_word_count
        self.last_day_node_count = self.today_node_count
        self.today_word_count = 0
        self.today_node_count = 0

    def render(self):
        return self.template.render(
            node_count=self.today_node_count,
            word_count=self.today_word_count,
            last_node_count=self.last_day_node_count,
            last_word_count=self.last_day_word_count,
        )
