from typing import List, Dict

from pydantic import BaseModel


class GetExtendedNodesResponse(BaseModel):
    class Node(BaseModel):
        id: str
        sourceNid: str
        sourceTitle: str
        title: str
        content: str
        searchTerms: List[str]

    requestId: str
    nodes: List[Node]


class LLMApiSettingsRequest(BaseModel):
    service: str
    model: str
    auth: Dict[str, str]


class LLMApiSettingsResponse(BaseModel):
    requestId: str
    service: str
    model: str
    auth: Dict[str, str]
