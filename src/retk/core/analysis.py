from typing import Tuple, Dict

from retk import const
from retk.models.client import client


async def get_marco_data() -> Tuple[Dict, const.CodeEnum]:
    user_count = await client.coll.users.count_documents({})
    node_count = await client.coll.nodes.count_documents({})
    return {
        "user_count": user_count,
        "node_count": node_count,
    }, const.CodeEnum.OK
