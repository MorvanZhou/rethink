from dataclasses import dataclass
from pathlib import Path
from typing import List

from bson import ObjectId

from retk import const
from retk.logger import logger
from .utils import parse_json_pattern, remove_links
from .. import api
from ..api.base import MessagesType

system_summary_prompt = (Path(__file__).parent / "system_summary.md").read_text(encoding="utf-8")
system_extend_prompt = (Path(__file__).parent / "system_extend.md").read_text(encoding="utf-8")


@dataclass
class ExtendCase:
    _id: ObjectId
    uid: str
    nid: str
    service: str
    model: str
    md: str
    stripped_md: str = ""
    summary: str = ""
    summary_code: const.CodeEnum = const.CodeEnum.OK
    extend: str = ""
    extend_code: const.CodeEnum = const.CodeEnum.OK

    def __post_init__(self):
        self.stripped_md = remove_links(self.md)


TOP_P = 0.9
TEMPERATURE = 0.4
TIMEOUT = 60

LLM_SERVICES = {
    "tencent": api.TencentService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
    "ali": api.AliyunService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
    "openai": api.OpenaiService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
    "moonshot": api.MoonshotService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
    "xf": api.XfYunService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
    "baidu": api.BaiduService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
}


async def _batch_send(
        is_extend: bool,
        system_prompt: str,
        cases: List[ExtendCase],
        req_id: str,
) -> List[ExtendCase]:
    svr_group = {}
    for case in cases:
        if case.service not in svr_group:
            svr_group[case.service] = {}
        if case.model not in svr_group[case.service]:
            svr_group[case.service][case.model] = {"case": [], "msgs": []}
        _m: MessagesType = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": case.summary if is_extend else case.stripped_md},
        ]
        svr_group[case.service][case.model]["case"].append(case)
        svr_group[case.service][case.model]["msgs"].append(_m)
    for service, models in svr_group.items():
        for model, model_cases in models.items():
            llm_service = LLM_SERVICES[service]
            results = await llm_service.batch_complete(
                messages=model_cases["msgs"],
                model=model,
                req_id=req_id,
            )
            for (_text, code), case in zip(results, model_cases["case"]):
                if is_extend:
                    case.extend = _text
                    case.extend_code = code
                else:
                    case.summary = _text
                    case.summary_code = code

                oneline_s = _text.replace('\n', '\\n')
                phase = "extend" if is_extend else "summary"
                logger.debug(f"reqId={req_id} | knowledge {phase}: {oneline_s}")
                if code != const.CodeEnum.OK:
                    logger.error(f"reqId={req_id} | knowledge {phase} error: {code}")
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
    cases = await _batch_send(
        is_extend=True,
        system_prompt=system_extend_prompt,
        cases=cases,
        req_id=req_id,
    )

    for case in cases:
        if case.extend_code != const.CodeEnum.OK:
            continue

        try:
            title, content = parse_json_pattern(case.extend)
        except ValueError as e:
            oneline = case.extend.replace('\n', '\\n')
            logger.error(f"reqId={req_id} | parse_json_pattern error: {e}. msg: {oneline}")
            case.extend_code = const.CodeEnum.LLM_INVALID_RESPONSE_FORMAT
        else:
            case.extend = f"{title}\n\n{content}"
    return cases
