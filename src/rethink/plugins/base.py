"""
This is the base class for all plugins. It is used to define the interface for all plugins.
The plugin can only be used in self-hosted mode,
because every customized plugin consumes resources.


Usage:

1. Create a new plugin by inheriting from `Plugin`:

    ```python
    import rethink

    class MyPlugin(rethink.Plugin):
        name = "MyPlugin"
        version = "0.1.0"
        description = "A demo plugin."
        author = "me"
        template = "<h1>{{ h1 }}</h1>\n<p>{{ p }}</p>"

        def before_node_updated(self, uid: str, nid: str, data: Dict[str, Any]) -> None:
            print("before_node_updated")
            data["md"] = "before_node_updated:" + data["md"]
    ```

2. Add the plugin to the system:

    ```python
    rethink.add_plugin(MyPlugin())
    ```

3. Run rethink server:

    ```python
    rethink.run()
    ```

4. Check when update a node, the `before_node_updated` text will show on your note.
"""

import inspect
from typing import Dict, List, Union, Optional, Any

from jinja2 import Template

from rethink import const
from rethink.models import tps
from .schedule.timing import Timing


class Plugin:
    """
    Attributes:
        name (str): The name of the plugin.
        version (str): The version of the plugin.
        description (str): The description of the plugin.
        author (str): The author of the plugin.
        template (Union[Template, str]): The template of the plugin.
        icon (str): The icon path for this plugin.
        activated (bool): Whether the plugin is activated.
        schedule_timing (Optional[Timing]): The schedule timing for the plugin if `on_schedule` method has been defined.
    """
    id: str
    name: str
    version: str = ""
    description: str = ""
    author: str = ""
    template: Union[Template, str] = ""
    icon: str = ""
    activated: bool = True
    schedule_timing: Optional[Timing] = None

    def __init__(self):
        for attr in ["id", "name", "version", "description", "author"]:
            if not hasattr(self, attr):
                raise ValueError(f"attribute '{attr}' is required")
        if len(self.id) == 0:
            raise ValueError("id is required")
        if len(self.id) > const.PLUGIN_ID_MAX_LENGTH:
            raise ValueError(f"id length should be less than {const.PLUGIN_ID_MAX_LENGTH}")

    def render(self) -> str:
        raise NotImplementedError

    def on_node_added(self, node: tps.Node) -> None:
        raise NotImplementedError

    def before_node_updated(self, uid: str, nid: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    def on_node_updated(self, node: tps.Node, old_md: str) -> None:
        raise NotImplementedError

    def on_schedule(self) -> None:
        raise NotImplementedError


event_plugin_map: Dict[str, List[Plugin]] = {
    "on_node_added": [],
    "before_node_updated": [],
    "on_node_updated": [],
    "on_schedule": [],
}
_plugins: Dict[str, Plugin] = {}


def add_plugin(plugin: Plugin):
    if plugin.id in _plugins:
        raise ValueError(f"plugin {plugin.id} already exists")
    _plugins[plugin.id] = plugin

    for method_name, value in event_plugin_map.items():
        cls = plugin.__class__
        method = getattr(cls, method_name, None)
        if method is None:
            continue

        for base_class in inspect.getmro(cls)[1:]:
            if method_name in base_class.__dict__ \
                    and method != base_class.__dict__[method_name]:  # redefined
                if plugin in value:
                    continue
                if method_name == "on_schedule" and plugin.schedule_timing is None:
                    raise ValueError(
                        f"schedule_timing is required for plugin.id={plugin.id} which implements on_schedule method."
                    )
                value.append(plugin)


def get_plugins() -> Dict[str, Plugin]:
    return _plugins


def remove_plugin(plugin: Plugin):
    del _plugins[plugin.id]

    for method_name, value in event_plugin_map.items():
        cls = plugin.__class__
        method = getattr(cls, method_name, None)
        if method is None:
            continue

        for base_class in inspect.getmro(cls)[1:]:
            if method_name in base_class.__dict__ \
                    and method != base_class.__dict__[method_name]:  # redefined
                try:
                    value.remove(plugin)
                except ValueError:
                    pass
