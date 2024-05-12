from bson import ObjectId

from retk import const
from retk.models.client import client


async def add_user_behavior(
        uid: str,
        type_: const.UserBehaviorTypeEnum,
        remark: str,
):
    await client.coll.user_behavior.insert_one({
        "_id": ObjectId(),
        "uid": uid,
        "type": type_.value,
        "remark": remark,
    })
