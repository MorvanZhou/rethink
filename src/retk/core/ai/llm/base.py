from abc import ABC, abstractmethod
from typing import List, Dict, Literal, AsyncIterable, Tuple

from retk import const

MessagesType = List[Dict[Literal["Role", "Content"], str]]


class BaseLLM(ABC):
    name: str = None

    def __init__(self):
        if self.name is None:
            raise ValueError("llm model name must be defined")

    @abstractmethod
    async def complete(self, *args, **kwargs) -> Tuple[str, const.CodeEnum]:
        ...

    @abstractmethod
    async def stream_complete(self, *args, **kwargs) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        ...
