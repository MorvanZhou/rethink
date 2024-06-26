from dataclasses import dataclass
from typing import Union, TYPE_CHECKING

from retk.depend.mongita.collection import Collection

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


@dataclass
class Collections:
    # base collections
    users: Union[Collection, "AsyncIOMotorCollection"] = None
    nodes: Union[Collection, "AsyncIOMotorCollection"] = None
    import_data: Union[Collection, "AsyncIOMotorCollection"] = None
    user_file: Union[Collection, "AsyncIOMotorCollection"] = None

    # notification
    notice_manager_delivery: Union[Collection, "AsyncIOMotorCollection"] = None
    notice_system: Union[Collection, "AsyncIOMotorCollection"] = None

    # user behavior
    user_behavior: Union[Collection, "AsyncIOMotorCollection"] = None

    # llm
    llm_extend_node_queue: Union[Collection, "AsyncIOMotorCollection"] = None
    llm_extended_node: Union[Collection, "AsyncIOMotorCollection"] = None
