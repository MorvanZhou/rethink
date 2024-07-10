from pathlib import Path
from typing import Tuple

from retk import const
from . import extended
from .extending import extend_on_node_update, extend_on_node_post, LLM_SERVICES
from ..api.base import BaseLLMService, MessagesType

system_summary_prompt = (Path(__file__).parent / "system_summary.md").read_text(encoding="utf-8")
system_extend_prompt = (Path(__file__).parent / "system_extend.md").read_text(encoding="utf-8")


async def _send(
        llm_service: BaseLLMService,
        model: str,
        system_prompt: str,
        md: str,
        req_id: str,
) -> Tuple[str, const.CodeEnum]:
    _msgs: MessagesType = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": md},
    ]
    return await llm_service.complete(messages=_msgs, model=model, req_id=req_id)


async def summary(
        llm_service: BaseLLMService,
        model: str,
        md: str,
        req_id: str = None,
) -> Tuple[str, const.CodeEnum]:
    return await _send(
        llm_service=llm_service,
        model=model,
        system_prompt=system_summary_prompt,
        md=md,
        req_id=req_id,
    )


async def extend(
        llm_service: BaseLLMService,
        model: str,
        md: str,
        req_id: str = None,
) -> Tuple[str, const.CodeEnum]:
    return await _send(
        llm_service=llm_service,
        model=model,
        system_prompt=system_extend_prompt,
        md=md,
        req_id=req_id,
    )
