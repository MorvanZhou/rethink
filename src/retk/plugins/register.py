from retk import config
from retk.logger import logger
from retk.plugins.base import add_plugin, remove_plugin
from retk.plugins.official_plugins.favorites.main import Favorites
from retk.plugins.official_plugins.summary.main import DailySummary

_official_plugins = [
    DailySummary(),
    Favorites(),
]


def register_official_plugins():
    if not config.get_settings().PLUGINS:
        return

    for _p in _official_plugins:
        add_plugin(_p)
        logger.debug(f"added plugin '{_p.name}' (id={_p.id})")


def unregister_official_plugins():
    if not config.get_settings().PLUGINS:
        return

    for _p in _official_plugins:
        remove_plugin(_p)
        logger.debug(f"removed plugin '{_p.name}' (id={_p.id})")
