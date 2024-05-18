import httpx

from retk import const, config
from retk.controllers import schemas
from retk.controllers.utils import maybe_raise_json_exception, json_exception
from retk.core import account, user, notice, analysis
from retk.models.tps import AuthedUser
from retk.utils import datetime2str


async def __get_then_set_github_user_id(au: AuthedUser, req: schemas.manager.GetUserRequest):
    if req.github.startswith("https://github.com/"):
        req.github = req.github.split("/", 4)[3]
    async with httpx.AsyncClient() as ac:
        url = f"https://api.github.com/users/{req.github}"
        try:
            resp = await ac.get(
                url=url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {config.get_settings().OAUTH_API_TOKEN_GITHUB}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                follow_redirects=False,
                timeout=5.
            )
        except (
                httpx.ConnectTimeout,
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.HTTPError
        ) as e:
            raise json_exception(
                request_id=au.request_id,
                code=const.CodeEnum.INVALID_PARAMS,
                log_msg=f"get github user info failed, error={e}",
            )
        if resp.status_code != 200:
            raise json_exception(
                request_id=au.request_id,
                code=const.CodeEnum.INVALID_PARAMS,
                log_msg=f"get github user info failed, status_code={resp.status_code}",
            )

        rj = resp.json()
        github_user_id = rj["id"]
        u, code = await user.get_account(
            account=str(github_user_id),
            source=const.UserSourceEnum.GITHUB.value,
            disabled=None,
            exclude_manager=True,
        )
        if code == const.CodeEnum.OK:
            req.uid = u["id"]


async def __check_user_uid(au: AuthedUser, req: schemas.manager.GetUserRequest) -> bool:
    if req.uid is None and req.email is None and req.github is None:
        raise json_exception(
            request_id=au.request_id,
            code=const.CodeEnum.INVALID_PARAMS,
            log_msg="uid and email and github can't be all None",
        )
    if req.github is not None:
        await __get_then_set_github_user_id(au=au, req=req)
    return req.uid is not None


async def get_manager_data(
        au: AuthedUser,
) -> schemas.manager.GetManagerDataResponse:
    data, code = await analysis.get_marco_data()
    maybe_raise_json_exception(au=au, code=code)
    return schemas.manager.GetManagerDataResponse(
        requestId=au.request_id,
        data=schemas.manager.GetManagerDataResponse.Data(
            userCount=data["user_count"],
            nodeCount=data["node_count"],
        )
    )


async def get_user_info(
        au: AuthedUser,
        req: schemas.manager.GetUserRequest,
) -> schemas.manager.GetUserResponse:
    if await __check_user_uid(au=au, req=req):
        u, code = await user.get(uid=req.uid, disabled=None, exclude_manager=True)
    else:
        u, code = await user.get_by_email(email=req.email, disabled=None, exclude_manager=True)
    maybe_raise_json_exception(au=au, code=code)
    return schemas.manager.GetUserResponse(
        requestId=au.request_id,
        user=schemas.manager.GetUserResponse.User(
            id=u["id"],
            source=u["source"],
            account=u["account"],
            nickname=u["nickname"],
            email=u["email"],
            avatar=u["avatar"],
            disabled=u["disabled"],
            createdAt=datetime2str(u["_id"].generation_time),
            modifiedAt=datetime2str(u["modifiedAt"]),
            usedSpace=u["usedSpace"],
            type=u["type"],
            lastState=schemas.manager.GetUserResponse.User.LastState(
                nodeDisplayMethod=u["lastState"]["nodeDisplayMethod"],
                nodeDisplaySortKey=u["lastState"]["nodeDisplaySortKey"],
                recentSearch=u["lastState"]["recentSearch"],
                recentCursorSearchSelectedNIds=u["lastState"]["recentCursorSearchSelectedNIds"],
            ),
            settings=schemas.manager.GetUserResponse.User.Settings(
                language=u["settings"]["language"],
                theme=u["settings"]["theme"],
                editorMode=u["settings"]["editorMode"],
                editorFontSize=u["settings"]["editorFontSize"],
                editorCodeTheme=u["settings"]["editorCodeTheme"],
                editorSepRightWidth=u["settings"]["editorSepRightWidth"],
                editorSideCurrentToolId=u["settings"]["editorSideCurrentToolId"],
            ),
        ),
    )


async def disable_account(
        au: AuthedUser,
        req: schemas.manager.GetUserRequest,
) -> schemas.RequestIdResponse:
    if await __check_user_uid(au=au, req=req):
        code = await account.manager.disable_by_uid(uid=req.uid)
    else:
        code = await account.manager.disable_by_email(email=req.email)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def enable_account(
        au: AuthedUser,
        req: schemas.manager.GetUserRequest,
) -> schemas.RequestIdResponse:
    if await __check_user_uid(au=au, req=req):
        code = await account.manager.enable_by_uid(uid=req.uid)
    else:
        code = await account.manager.enable_by_email(email=req.email)
    maybe_raise_json_exception(au=au, code=code)
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def delete_account(
        au: AuthedUser,
        req: schemas.manager.GetUserRequest,
) -> schemas.RequestIdResponse:
    if await __check_user_uid(au=au, req=req):
        await account.manager.delete_by_uid(uid=req.uid)
    else:
        await account.manager.delete_by_email(email=req.email)
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def post_in_manager_delivery(
        au: AuthedUser,
        req: schemas.manager.ManagerNoticeDeliveryRequest,
) -> schemas.RequestIdResponse:
    _, code = await notice.post_in_manager_delivery(
        au=au,
        title=req.title,
        content=req.content,
        recipient_type=req.recipientType,
        batch_type_ids=req.batchTypeIds,
        publish_at=req.publishAt,
    )
    maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def get_system_notices(
        au: AuthedUser,
        page: int,
        limit: int,
) -> schemas.manager.GetSystemNoticesResponse:
    notices, total = await notice.get_system_notices(
        page=page,
        limit=limit,
    )
    for n in notices:
        n["id"] = str(n["_id"])
        del n["_id"]
    return schemas.manager.GetSystemNoticesResponse(
        requestId=au.request_id,
        notices=notices,
        total=total,
    )
