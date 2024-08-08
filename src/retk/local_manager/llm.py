import json
from typing import Dict, Optional

from retk import config
from retk.core.ai.llm.api import LLM_SERVICES_CLASS
from retk.local_manager.recover import (
    DotRethinkSettingsLLMApi, load_dot_rethink, dump_default_dot_rethink, get_dot_rethink_path
)


def set_llm_api_to_config():
    api_settings: Optional[DotRethinkSettingsLLMApi] = get_llm_api_settings()
    settings = config.get_settings()
    if api_settings is None:
        try:
            LLM_SERVICES_CLASS[settings.LLM_KNOWLEDGE_SUMMARY_SERVICE]["service"].set_api_auth({})
        except KeyError:
            pass
        else:
            settings.LLM_KNOWLEDGE_SUMMARY_SERVICE = ""
            settings.LLM_KNOWLEDGE_SUMMARY_MODEL = ""
            settings.LLM_KNOWLEDGE_EXTEND_SERVICE = ""
            settings.LLM_KNOWLEDGE_EXTEND_MODEL = ""
        return

    service = api_settings.get("service", "")
    model = api_settings.get("model", "")
    settings.LLM_KNOWLEDGE_SUMMARY_SERVICE = service
    settings.LLM_KNOWLEDGE_SUMMARY_MODEL = model
    settings.LLM_KNOWLEDGE_EXTEND_SERVICE = service
    settings.LLM_KNOWLEDGE_EXTEND_MODEL = model

    try:
        LLM_SERVICES_CLASS[service]["service"].set_api_auth(api_settings.get("auth", {}))
    except KeyError:
        pass


def get_llm_api_settings() -> Optional[DotRethinkSettingsLLMApi]:
    dot_rethink = load_dot_rethink()
    if dot_rethink is None:
        return None
    return dot_rethink["settings"]["llmApi"]


def change_llm_api(
        llm_service: str,
        llm_model: str,
        llm_api_auth: Dict[str, str],
):
    if llm_service not in LLM_SERVICES_CLASS:
        raise ValueError(f"{llm_service} not in ALL_SERVICES: {LLM_SERVICES_CLASS.keys()}")
    model_keys = [i.value.key for i in LLM_SERVICES_CLASS[llm_service]["models"].__members__.values()]
    if llm_model not in model_keys:
        raise ValueError(f"{llm_service}: {llm_model} not in {model_keys}")
    if len(llm_api_auth) == 0:
        raise ValueError("api auth is empty")

    dot_rethink = load_dot_rethink()
    if dot_rethink is None:
        dot_rethink = dump_default_dot_rethink()
    dot_rethink["settings"]["llmApi"] = DotRethinkSettingsLLMApi(
        service=llm_service,
        model=llm_model,
        auth=llm_api_auth,
    )
    with open(get_dot_rethink_path(), "w", encoding="utf-8") as f:
        json.dump(dot_rethink, f, indent=2, ensure_ascii=False)

    set_llm_api_to_config()
    return dot_rethink


def delete_llm_api():
    dot_rethink = load_dot_rethink()
    if dot_rethink is None:
        return
    dot_rethink["settings"]["llmApi"] = None
    with open(get_dot_rethink_path(), "w", encoding="utf-8") as f:
        json.dump(dot_rethink, f, indent=2, ensure_ascii=False)
    set_llm_api_to_config()
    return dot_rethink
