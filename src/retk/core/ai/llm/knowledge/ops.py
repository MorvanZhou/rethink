from dataclasses import dataclass
from pathlib import Path
from typing import List

from bson import ObjectId

from retk import const
from retk.logger import logger
from ..api import LLM_DEFAULT_SERVICES
from ..api.base import MessagesType
from ..utils import remove_links

system_summary_prompt = (Path(__file__).parent / "system_summary.md").read_text(encoding="utf-8")
system_extend_prompt = (Path(__file__).parent / "system_extend.md").read_text(encoding="utf-8")


@dataclass
class ExtendCase:
    _id: ObjectId
    uid: str
    nid: str
    summary_service: str
    summary_model: str
    extend_service: str
    extend_model: str
    md: str
    stripped_md: str = ""
    summary: str = ""
    summary_code: const.CodeEnum = const.CodeEnum.OK
    extend_title: str = ""
    extend_content: str = ""
    extend_search_terms: List[str] = None
    extend_code: const.CodeEnum = const.CodeEnum.OK

    def __post_init__(self):
        self.stripped_md = remove_links(self.md)

    @property
    def extend_md(self):
        return f"{self.extend_title}\n\n{self.extend_content}"


async def _batch_send(
        is_extend: bool,
        system_prompt: str,
        cases: List[ExtendCase],
        req_id: str,
) -> List[ExtendCase]:
    svr_group = {}
    for case in cases:
        if is_extend:
            if case.summary_code != const.CodeEnum.OK:
                continue
            service = case.extend_service
            model = case.extend_model
            content = case.summary
        else:
            service = case.summary_service
            model = case.summary_model
            content = case.stripped_md

        if service not in svr_group:
            svr_group[service] = {}
        if model not in svr_group[service]:
            svr_group[service][model] = {"case": [], "msgs": []}
        _m: MessagesType = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]
        svr_group[service][model]["case"].append(case)
        svr_group[service][model]["msgs"].append(_m)

    for service, models in svr_group.items():
        for model, model_cases in models.items():
            llm_service = LLM_DEFAULT_SERVICES[service]
            if is_extend:
                results = await llm_service.batch_complete_json_detect(
                    messages=model_cases["msgs"],
                    model=model,
                    req_id=req_id,
                )
            else:
                results = await llm_service.batch_complete(
                    messages=model_cases["msgs"],
                    model=model,
                    req_id=req_id,
                )
            for (_data, code), case in zip(results, model_cases["case"]):
                if is_extend:
                    case.extend_title = _data.get("title", _data.get("标题", ""))
                    case.extend_content = _data.get("content", _data.get("内容", ""))
                    case.extend_search_terms = _data.get("searchTerms", _data.get("关键词", ""))
                    case.extend_code = code
                    oneline_s = case.extend_md.replace('\n', '\\n')
                else:
                    case.summary = _data
                    case.summary_code = code
                    oneline_s = _data.replace('\n', '\\n')

                phase = "extend" if is_extend else "summary"
                logger.debug(
                    f"rid='{req_id}' "
                    f"| uid='{case.uid}' "
                    f"| knowledge {phase} "
                    f"| {service} {model} "
                    f"| response='{oneline_s}'"
                )
                if code != const.CodeEnum.OK:
                    oneline = case.stripped_md.replace('\n', '\\n')
                    logger.error(
                        f"rid='{req_id}' "
                        f"| uid='{case.uid}' "
                        f"| knowledge {phase} "
                        f"| {service} {model} "
                        f"| error: {code.name} "
                        f"| summary: {oneline}"
                    )
    return cases


async def batch_summary(
        cases: List[ExtendCase],
        req_id: str = None,
) -> List[ExtendCase]:
    return await _batch_send(
        is_extend=False,
        system_prompt=system_summary_prompt,
        cases=cases,
        req_id=req_id,
    )


async def batch_extend(
        cases: List[ExtendCase],
        req_id: str = None,
) -> List[ExtendCase]:
    return await _batch_send(
        is_extend=True,
        system_prompt=system_extend_prompt,
        cases=cases,
        req_id=req_id,
    )
