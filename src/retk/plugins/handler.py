from typing import Callable

from retk.const import CodeEnum
from retk.models.tps import AuthedUser
from .base import event_plugin_map


def on_node_added(func: Callable):
    async def wrapper(*args, **kwargs):
        data, code = await func(*args, **kwargs)
        if code != CodeEnum.OK:
            return data, code
        for inst in event_plugin_map["on_node_added"]:
            # execute the class method
            inst.on_node_added(node=data)
        return data, code

    return wrapper


def on_node_updated(func: Callable):
    async def wrapper(
            au: AuthedUser,
            nid: str,
            md: str,
            *args, **kwargs,
    ):
        data, old_data, code = await func(
            au=au,
            nid=nid,
            md=md,
            *args, **kwargs
        )
        if code != CodeEnum.OK:
            return data, code
        for inst in event_plugin_map["on_node_updated"]:
            # execute the class method
            inst.on_node_updated(node=data, old_node=old_data)
        return data, old_data, code

    return wrapper


def before_node_updated(func: Callable):
    async def wrapper(
            au: AuthedUser,
            nid: str,
            md: str,
            *args, **kwargs,
    ):
        data = {"md": md}
        for inst in event_plugin_map["before_node_updated"]:
            # execute the class method
            inst.before_node_updated(
                uid=au.u.id,
                nid=nid,
                data=data,
            )
        return await func(
            au=au,
            nid=nid,
            md=data["md"],
            *args, **kwargs
        )

    return wrapper
