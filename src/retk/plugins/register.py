from retk import config
from retk.logger import logger
from retk.plugins.base import add_plugin, remove_plugin
from retk.plugins.official_plugins.favorites.main import Favorites
from retk.plugins.official_plugins.summary.main import DailySummary

_official_plugins = [
    DailySummary,
    Favorites,
]

_registered_official_plugins = []


def register_official_plugins():
    if not config.get_settings().PLUGINS:
        return

    for _p in _official_plugins:
        _p_instance = _p()
        add_plugin(_p_instance)
        _registered_official_plugins.append(_p_instance)
        logger.debug(f"added plugin '{_p.name}' (id={_p.id})")


def unregister_official_plugins():
    if not config.get_settings().PLUGINS:
        return

    for _p in _registered_official_plugins:
        remove_plugin(_p)
        logger.debug(f"removed plugin '{_p.name}' (id={_p.id})")
