from retk.models.coll import Collections

IS_MOTOR = True
try:
    from motor.motor_asyncio import AsyncIOMotorCollection
except ImportError:
    IS_MOTOR = False


async def remote_try_build_index(coll: Collections):
    # try creating index
    if not IS_MOTOR:
        return

    await users_coll(coll.users)
    await nodes_coll(coll.nodes)
    await import_data_coll(coll.import_data)
    await user_file_coll(coll.user_file)
    await user_behavior_coll(coll.user_behavior)
    await notice_manager_delivery_coll(coll.notice_manager_delivery)
    await notice_system_coll(coll.notice_system)


async def not_in_and_create_index(coll: "AsyncIOMotorCollection", index_info, keys: list, unique: bool) -> str:
    new_keys = []
    for k in keys:
        if isinstance(k, tuple):
            new_keys.append(f"{k[0]}_{k[1]}")
        elif isinstance(k, str):
            new_keys.append(f"{k}_1")
        else:
            raise ValueError(f"Invalid key: {k}")
    index = "_".join(new_keys)
    if index not in index_info:
        await coll.create_index(keys, unique=unique)
    return index


async def users_coll(coll: "AsyncIOMotorCollection"):
    index_info = await coll.index_information()
    await not_in_and_create_index(
        coll=coll,
        index_info=index_info,
        keys=["id"],
        unique=True
    )
    await not_in_and_create_index(
        coll=coll,
        index_info=index_info,
        keys=["account", "source"],
        unique=True
    )


async def nodes_coll(coll: "AsyncIOMotorCollection"):
    index_info = await coll.index_information()
    await not_in_and_create_index(
        coll=coll,
        index_info=index_info,
        keys=["id"],
        unique=True
    )
    await not_in_and_create_index(
        coll=coll,
        index_info=index_info,
        keys=[("uid", 1), ("id", -1)],
        unique=True
    )


async def import_data_coll(coll: "AsyncIOMotorCollection"):
    import_data_info = await coll.index_information()
    await not_in_and_create_index(
        coll=coll,
        index_info=import_data_info,
        keys=["uid"],
        unique=True
    )


async def user_file_coll(coll: "AsyncIOMotorCollection"):
    user_file_info = await coll.index_information()
    await not_in_and_create_index(
        coll=coll,
        index_info=user_file_info,
        keys=[("uid", 1), ("fid", -1)],
        unique=True
    )


async def user_behavior_coll(coll: "AsyncIOMotorCollection"):
    user_behavior_info = await coll.index_information()
    await not_in_and_create_index(
        coll=coll,
        index_info=user_behavior_info,
        keys=["uid", "type"],
        unique=False
    )


async def notice_manager_delivery_coll(coll: "AsyncIOMotorCollection"):
    index_info = await coll.index_information()
    await not_in_and_create_index(
        coll=coll,
        index_info=index_info,
        keys=["senderId"],
        unique=False
    )
    await not_in_and_create_index(
        coll=coll,
        index_info=index_info,
        keys=["scheduled"],
        unique=False
    )


async def notice_system_coll(coll: "AsyncIOMotorCollection"):
    index_info = await coll.index_information()
    await not_in_and_create_index(
        coll=coll,
        index_info=index_info,
        keys=["recipientId", "read"],
        unique=False
    )
    await not_in_and_create_index(
        coll=coll,
        index_info=index_info,
        keys=["senderId"],
        unique=False
    )
