from pathlib import Path
from typing import Tuple

from retk import const
from retk.logger import logger
from .utils import parse_json_pattern, remove_links
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
    md_ = remove_links(md)
    return await _send(
        llm_service=llm_service,
        model=model,
        system_prompt=system_summary_prompt,
        md=md_,
        req_id=req_id,
    )


async def extend(
        llm_service: BaseLLMService,
        model: str,
        md: str,
        req_id: str = None,
) -> Tuple[str, const.CodeEnum]:
    msg, code = await _send(
        llm_service=llm_service,
        model=model,
        system_prompt=system_extend_prompt,
        md=md,
        req_id=req_id,
    )
    if code != const.CodeEnum.OK:
        return msg, code

    try:
        title, content = parse_json_pattern(msg)
    except ValueError as e:
        logger.error(f"parse_json_pattern error: {e}. msg: {msg}")
        return str(e), const.CodeEnum.LLM_INVALID_RESPONSE_FORMAT
    return f"{title}\n\n{content}", const.CodeEnum.OK
