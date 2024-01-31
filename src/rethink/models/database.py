from rethink.models.client import client


async def init():
    await client.init()
