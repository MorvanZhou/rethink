from typing import Dict

from .aliyun import AliyunService, AliyunModelEnum
from .baidu import BaiduService, BaiduModelEnum
from .base import BaseLLMService
from .moonshot import MoonshotService, MoonshotModelEnum
from .openai import OpenaiService, OpenaiModelEnum
from .tencent import TencentService, TencentModelEnum
from .xfyun import XfYunService, XfYunModelEnum

LLM_SERVICES_CLASS = {
    AliyunService.name: {
        "service": AliyunService,
        "models": AliyunModelEnum,
    },
    BaiduService.name: {
        "service": BaiduService,
        "models": BaiduModelEnum,
    },
    MoonshotService.name: {
        "service": MoonshotService,
        "models": MoonshotModelEnum,
    },
    OpenaiService.name: {
        "service": OpenaiService,
        "models": OpenaiModelEnum,
    },
    TencentService.name: {
        "service": TencentService,
        "models": TencentModelEnum,
    },
    XfYunService.name: {
        "service": XfYunService,
        "models": XfYunModelEnum,
    },
}

TOP_P = 0.9
TEMPERATURE = 0.6
TIMEOUT = 60

LLM_DEFAULT_SERVICES: Dict[str, BaseLLMService] = {
    s.name: s(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT) for s in [
        TencentService,
        AliyunService,
        OpenaiService,
        MoonshotService,
        XfYunService,
        BaiduService,
    ]
}
