import shutil
import unittest
from pathlib import Path
from typing import Dict

import rethink
from rethink import core, const
from rethink.models.client import client
from rethink.plugins.base import event_plugin_map
from . import utils


class TestPlugin(rethink.Plugin):
    id = "testPlugin"
    name = "TestPlugin"
    version = "0.1.0"
    description = "A demo test plugin."
    author = "morvanzhou"
    template = "<h1>{h}</h1>\n<p>{p}</p>"

    def __init__(self):
        super().__init__()
        self.cache: Dict[str, rethink.tps.Node] = {}
        self.bmd = ""
        self.h = ""
        self.p = ""

    def render(self):
        return self.template.format(h=self.h, p=self.p)

    def on_node_added(self, node: rethink.tps.Node):
        self.cache[node["id"]] = node

    def before_node_updated(self, uid: str, nid: str, data: Dict[str, str]):
        self.bmd = "before_node_updated:" + data["md"]

    def on_node_updated(self, node: rethink.tps.Node, old_md: str):
        self.cache[node["id"]] = node


class DemoCount(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")
        shutil.rmtree(Path(__file__).parent / "tmp", ignore_errors=True)

    async def asyncSetUp(self) -> None:
        self.p = TestPlugin()
        rethink.add_plugin(self.p)

        await client.init()
        u, _ = await core.user.get_by_email(email=const.DEFAULT_USER["email"])
        self.uid = u["id"]

    async def asyncTearDown(self) -> None:
        rethink.remove_plugin(self.p)
        await client.drop()
        shutil.rmtree(Path(__file__).parent / "tmp" / ".data" / "files", ignore_errors=True)
        shutil.rmtree(Path(__file__).parent / "tmp" / ".data" / "md", ignore_errors=True)

    def test_creation(self):
        self.assertEqual(self.p.id, "testPlugin")
        self.assertEqual(self.p.name, "TestPlugin")
        self.assertEqual(self.p.version, "0.1.0")
        self.assertEqual(self.p.description, "A demo test plugin.")
        self.assertEqual(self.p.author, "morvanzhou")

    def test_render(self):
        self.p.h = "test h1"
        self.p.p = "test p"
        self.assertEqual(
            "<h1>test h1</h1>\n<p>test p</p>",
            self.p.render()
        )

    def test_set_template_from_file(self):
        self.p.template = "<h2>{h}</h2>\n<p>{p}</p>"
        self.p.h = "test h"
        self.p.p = "test p"
        self.assertEqual(
            "<h2>test h</h2>\n<p>test p</p>",
            self.p.render()
        )

    async def test_event(self):
        print(event_plugin_map["on_node_added"])
        self.assertIn(self.p, event_plugin_map["on_node_added"])

        node, code = await core.node.add(
            uid=self.uid, md="a", type_=const.NodeType.MARKDOWN.value
        )
        self.assertEqual(rethink.const.Code.OK, code)
        self.assertEqual(node, self.p.cache[node["id"]])
        self.assertEqual("a", self.p.cache[node["id"]]["md"])

        self.assertEqual("", self.p.bmd)
        node, code = await core.node.update(
            uid=self.uid, nid=node["id"], md="b"
        )
        self.assertEqual(rethink.const.Code.OK, code)
        self.assertEqual(node, self.p.cache[node["id"]])
        self.assertEqual("b", self.p.cache[node["id"]]["md"])
        self.assertEqual("before_node_updated:b", self.p.bmd)

    def test_timing(self):
        with self.assertRaises(ValueError):
            rethink.schedule.every_minute_at(second=-1)
        t = rethink.schedule.every_minute_at(second=1)
        self.assertEqual(1, t.at_second)
        self.assertEqual(0, t.at_minute)
