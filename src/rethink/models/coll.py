from dataclasses import dataclass
from typing import Union

from rethink.depend.mongita.collection import Collection


@dataclass
class Collections:
    users: Union[Collection, "AsyncIOMotorCollection"] = None
    nodes: Union[Collection, "AsyncIOMotorCollection"] = None
    import_data: Union[Collection, "AsyncIOMotorCollection"] = None
    user_file: Union[Collection, "AsyncIOMotorCollection"] = None
