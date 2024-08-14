from retk import config, core, const
from retk.controllers import schemas
from retk.controllers.account import __login
from retk.controllers.node.node_ops import get_node_data
from retk.controllers.utils import maybe_raise_json_exception
from retk.models.tps import AuthedUser
from retk.utils import jwt_encode


async def browser_extension_login(
        req_id: str,
        req: schemas.account.LoginRequest,
) -> schemas.browser_extension.LoginTokenResponse:
    access_token, refresh_token, u = await __login(req_id=req_id, req=req)
    return schemas.browser_extension.LoginTokenResponse(
        requestId=req_id,
        accessToken=access_token,
        refreshToken=refresh_token,
        nickname=u["nickname"],
        uid=u["id"],
    )


async def get_access_token(
        au: AuthedUser,
) -> schemas.browser_extension.LoginTokenResponse:
    access_token = jwt_encode(
        exp_delta=config.get_settings().ACCESS_TOKEN_EXPIRE_DELTA,
        data={
            "is_access": True,
            "uid": au.u.id,
            "language": au.language,
        },
    )
    return schemas.browser_extension.LoginTokenResponse(
        requestId=au.request_id,
        accessToken=access_token,
        refreshToken="",
        nickname="",
        uid="",
    )


async def post_node(
        au: AuthedUser,
        req: schemas.browser_extension.CreateNodeRequest,
) -> schemas.node.NodeResponse:
    if au.language == const.LanguageEnum.ZH.value:
        source_prefix = "原文来自:"
    elif au.language == const.LanguageEnum.EN.value:
        source_prefix = "Source from:"
    else:
        source_prefix = "Source from:"
    md = f"{req.title}\n\n{source_prefix} [{req.url}]({req.url})\n\n{req.content}"
    n, code = await core.node.post(
        au=au,
        md=md,
        type_=const.NodeTypeEnum.MARKDOWN.value,
        from_nid="",
    )
    maybe_raise_json_exception(au=au, code=code)
    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.NODE_BROWSER_EXTENSION_CREATE,
        remark=n['id'],
    )
    return schemas.node.NodeResponse(
        requestId=au.request_id,
        node=get_node_data(n),
    )
