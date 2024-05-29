from typing import Tuple, Dict

from retk import const
from retk.models.client import client


async def get_marco_data() -> Tuple[Dict, const.CodeEnum]:
    user_count = {}
    for name, value in const.user_sources.UserSourceEnum.__members__.items():
        user_count[name] = await client.coll.users.count_documents({"source": value})

    user_total_count = sum(user_count.values())
    user_count["total"] = user_total_count
    node_count = await client.coll.nodes.count_documents({})
    return {
        "user_count": user_count,
        "node_count": node_count,
    }, const.CodeEnum.OK
