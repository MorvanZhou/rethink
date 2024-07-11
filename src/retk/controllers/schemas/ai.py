from typing import List

from pydantic import BaseModel


class GetExtendedNodesResponse(BaseModel):
    class Node(BaseModel):
        id: str
        sourceNid: str
        sourceTitle: str
        title: str
        content: str

    requestId: str
    nodes: List[Node]
