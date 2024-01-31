from dataclasses import dataclass
from typing import Union, TYPE_CHECKING

from rethink.depend.mongita.collection import Collection

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


@dataclass
class Collections:
    users: Union[Collection, "AsyncIOMotorCollection"] = None
    nodes: Union[Collection, "AsyncIOMotorCollection"] = None
    import_data: Union[Collection, "AsyncIOMotorCollection"] = None
    user_file: Union[Collection, "AsyncIOMotorCollection"] = None
