from retk import const, local_manager
from retk.config import is_local_db
from retk.controllers import schemas
from retk.controllers.utils import json_exception, maybe_raise_json_exception
from retk.core.ai.llm.api import LLM_DEFAULT_SERVICES
from retk.models.tps import AuthedUser


async def get_llm_api_settings(
        au: AuthedUser,
) -> schemas.ai.LLMApiSettingsResponse:
    if not is_local_db():
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.NOT_PERMITTED,
            language=au.language,
        )
    llm_settings = local_manager.llm.get_llm_api_settings()
    if llm_settings is None:
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.INVALID_SETTING,
            language=au.language,
        )
    return schemas.ai.LLMApiSettingsResponse(
        requestId=au.request_id,
        service=llm_settings.get("service", ""),
        model=llm_settings.get("model", ""),
        auth=llm_settings.get("auth", {}),
    )


async def change_llm_api_settings(
        au: AuthedUser,
        req: schemas.ai.LLMApiSettingsRequest,
) -> schemas.ai.LLMApiSettingsResponse:
    if not is_local_db():
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.NOT_PERMITTED,
            language=au.language,
        )
    try:
        local_manager.llm.change_llm_api(
            llm_service=req.service,
            llm_model=req.model,
            llm_api_auth=req.auth,
        )
    except ValueError as e:
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.INVALID_SETTING,
            language=au.language,
            log_msg=str(e),
        )
    return schemas.ai.LLMApiSettingsResponse(
        requestId=au.request_id,
        service=req.service,
        model=req.model,
        auth=req.auth,
    )


async def delete_llm_api_settings(
        au: AuthedUser,
) -> schemas.RequestIdResponse:
    if not is_local_db():
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.NOT_PERMITTED,
            language=au.language,
        )
    local_manager.llm.delete_llm_api()
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def llm_api_test(
        au: AuthedUser,
) -> schemas.RequestIdResponse:
    if not is_local_db():
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.NOT_PERMITTED,
            language=au.language,
        )
    llm_api = local_manager.llm.get_llm_api_settings()
    if llm_api is None:
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.INVALID_SETTING,
            language=au.language,
            log_msg="llm_api is None",
        )
    service = llm_api.get("service")
    if service not in LLM_DEFAULT_SERVICES:
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.INVALID_SETTING,
            language=au.language,
            log_msg=f"{service} not in LLM_DEFAULT_SERVICES: {LLM_DEFAULT_SERVICES.keys()}",
        )
    model = llm_api.get("model")
    if model is None:
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.INVALID_SETTING,
            language=au.language,
            log_msg=f"model is None",
        )
    auth = llm_api.get("auth")
    if auth is None or len(auth) == 0:
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.INVALID_SETTING,
            language=au.language,
            log_msg=f"auth is None or empty",
        )
    llm_service = LLM_DEFAULT_SERVICES[service]
    resp, code = await llm_service.complete(
        messages=[{"role": "user", "content": "hi"}],
        model=model,
        req_id=au.request_id,
    )
    print(resp)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )
