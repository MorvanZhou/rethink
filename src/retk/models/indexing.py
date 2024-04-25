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


async def users_coll(coll: "AsyncIOMotorCollection"):
    users_info = await coll.index_information()
    if "id_1" not in users_info:
        await coll.create_index("id", unique=True)
    if "account_1_source_1" not in users_info:
        await coll.create_index(["account", "source"], unique=True)


async def nodes_coll(coll: "AsyncIOMotorCollection"):
    nodes_info = await coll.index_information()
    if "id_1" not in nodes_info:
        await coll.create_index("id", unique=True)
    if "uid_1_id_-1" not in nodes_info:
        # created at
        await coll.create_index(
            [("uid", 1), ("id", -1)],
            unique=True,
        )


async def import_data_coll(coll: "AsyncIOMotorCollection"):
    import_data_info = await coll.index_information()
    if "uid_1" not in import_data_info:
        await coll.create_index("uid", unique=True)


async def user_file_coll(coll: "AsyncIOMotorCollection"):
    user_file_info = await coll.index_information()
    if "uid_1_fid_-1" not in user_file_info:
        await coll.create_index([("uid", 1), ("fid", -1)], unique=True)


async def user_behavior_coll(coll: "AsyncIOMotorCollection"):
    user_behavior_info = await coll.index_information()
    if "uid_1_type_1" not in user_behavior_info:
        await coll.create_index([("uid", 1), ("type", 1)], unique=True)
