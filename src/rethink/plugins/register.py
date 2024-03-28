from rethink import config
from rethink.logger import logger
from rethink.plugins.base import add_plugin
from rethink.plugins.official_plugins.favorites.main import Favorites
from rethink.plugins.official_plugins.summary.main import DailySummary


def register_official_plugins():
    if not config.get_settings().PLUGINS:
        return

    for _p_cls in [
        DailySummary,
        Favorites,
    ]:
        add_plugin(_p_cls())
        logger.info(f"added plugin '{_p_cls.name}' (id={_p_cls.id})")
