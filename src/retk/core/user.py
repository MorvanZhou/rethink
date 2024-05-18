import datetime
import html
from typing import Optional, Tuple

from bson import ObjectId
from bson.tz_util import utc
from pymongo.errors import DuplicateKeyError

from retk import const, config, utils
from retk.controllers.schemas.user import PatchUserRequest
from retk.models import tps
from retk.models.client import client


async def add(
        account: str,
        source: int,
        email: str,
        hashed: str,
        nickname: str,
        avatar: str,
        language: str,
) -> Tuple[Optional[tps.UserMeta], const.CodeEnum]:
    if await client.coll.users.find_one({"account": account, "source": source}) is not None:
        return None, const.CodeEnum.EMAIL_OCCUPIED
    oid = ObjectId()
    # assert language in const.Language
    if not const.LanguageEnum.is_valid(language):
        language = const.LanguageEnum.EN.value
    data = utils.get_user_dict(
        _id=oid,
        uid=utils.short_uuid(),
        source=source,
        account=account,
        nickname=nickname,
        email=email,
        avatar=str(avatar),
        hashed=hashed,
        disabled=False,
        modified_at=oid.generation_time,
        used_space=0,
        type_=const.USER_TYPE.NORMAL.id,

        last_state_recent_cursor_search_selected_nids=[],
        last_state_recent_search=[],
        last_state_node_display_method=const.NodeDisplayMethodEnum.CARD.value,
        last_state_node_display_sort_key="modifiedAt",

        settings_language=language,
        settings_theme=const.app.AppThemeEnum.LIGHT.value,
        settings_editor_mode=const.app.EditorModeEnum.WYSIWYG.value,
        settings_editor_font_size=15,
        settings_editor_code_theme=const.app.EditorCodeThemeEnum.GITHUB.value,
        settings_editor_sep_right_width=200,
        settings_editor_side_current_tool_id="",
    )

    # catch if id is duplicated
    while True:
        try:
            res = await client.coll.users.insert_one(data)
            if not res.acknowledged:
                return None, const.CodeEnum.OPERATION_FAILED
            break
        except DuplicateKeyError:
            data["id"] = utils.short_uuid()
            continue

    return data, const.CodeEnum.OK


async def patch(  # noqa: C901
        au: tps.AuthedUser,
        req: PatchUserRequest,
) -> Tuple[Optional[tps.UserMeta], const.CodeEnum]:
    new_data = {}

    if req.nickname is not None:
        nickname = req.nickname.strip()
        nickname = html.escape(nickname)
        if nickname != "":
            new_data["nickname"] = nickname

    if req.avatar is not None:
        avatar = str(req.avatar).strip()
        if avatar != "":
            new_data["avatar"] = avatar

    if req.lastState is not None:
        if req.lastState.nodeDisplayMethod is not None:
            if req.lastState.nodeDisplayMethod >= len(
                    const.NodeDisplayMethodEnum) or req.lastState.nodeDisplayMethod < 0:
                return None, const.CodeEnum.INVALID_NODE_DISPLAY_METHOD
            new_data["lastState.nodeDisplayMethod"] = req.lastState.nodeDisplayMethod

        if req.lastState.nodeDisplaySortKey is not None:
            new_data["lastState.nodeDisplaySortKey"] = req.lastState.nodeDisplaySortKey

    if req.settings is not None:
        if req.settings.language is not None:
            new_data["settings.language"] = req.settings.language

        if req.settings.theme is not None:
            new_data["settings.theme"] = req.settings.theme

        if req.settings.editorMode is not None:
            new_data["settings.editorMode"] = req.settings.editorMode

        if req.settings.editorFontSize is not None:
            if not const.app.EditorFontSizeEnum.is_valid(req.settings.editorFontSize):
                return None, const.CodeEnum.INVALID_SETTING
            new_data["settings.editorFontSize"] = req.settings.editorFontSize

        if req.settings.editorCodeTheme is not None:
            new_data["settings.editorCodeTheme"] = req.settings.editorCodeTheme

        if req.settings.editorSepRightWidth is not None:
            new_data["settings.editorSepRightWidth"] = req.settings.editorSepRightWidth

        if req.settings.editorSideCurrentToolId is not None:
            new_data["settings.editorSideCurrentToolId"] = req.settings.editorSideCurrentToolId

    # has data to update
    if len(new_data) != 0:
        new_data["modifiedAt"] = datetime.datetime.now(tz=utc)

        res = await client.coll.users.update_one(
            {"id": au.u.id},
            {"$set": new_data},
        )
        if res.modified_count != 1:
            return None, const.CodeEnum.OPERATION_FAILED

    return await get(uid=au.u.id, disabled=None)


def __get_user_condition(condition: dict, exclude_manager: bool) -> dict:
    if exclude_manager:
        condition["type"] = {"$nin": [
            const.user_types.USER_TYPE.ADMIN.id,
            const.user_types.USER_TYPE.MANAGER.id,
        ]}
    return condition


async def get_by_email(
        email: str,
        disabled: Optional[bool] = False,
        exclude_manager: bool = False,
) -> Tuple[Optional[tps.UserMeta], const.CodeEnum]:
    if config.get_settings().ONE_USER:
        source = const.UserSourceEnum.LOCAL.value
    else:
        source = const.UserSourceEnum.EMAIL.value
    return await get_account(account=email, source=source, disabled=disabled, exclude_manager=exclude_manager)


async def get_account(
        account: str,
        source: int,
        disabled: Optional[bool] = False,
        exclude_manager: bool = False,
) -> Tuple[Optional[tps.UserMeta], const.CodeEnum]:
    c = {"source": source, "account": account}
    if disabled is not None:
        c["disabled"] = disabled
    c = __get_user_condition(condition=c, exclude_manager=False)  # exclude_manager)
    u = await client.coll.users.find_one(c)
    if u is None:
        return None, const.CodeEnum.ACCOUNT_OR_PASSWORD_ERROR
    return u, const.CodeEnum.OK


async def get(
        uid: str,
        disabled: Optional[bool] = False,
        exclude_manager: bool = False
) -> Tuple[Optional[tps.UserMeta], const.CodeEnum]:
    c = {"id": uid}
    if disabled is not None:
        c["disabled"] = disabled
    c = __get_user_condition(condition=c, exclude_manager=exclude_manager)
    u = await client.coll.users.find_one(c)
    if u is None:
        return None, const.CodeEnum.USER_NOT_EXIST
    if u["usedSpace"] < 0:
        # reset usedSpace to 0
        await client.coll.users.update_one(
            {"id": uid},
            {"$set": {"usedSpace": 0}}
        )
        u["usedSpace"] = 0

    return u, const.CodeEnum.OK


async def update_used_space(uid: str, delta: int) -> const.CodeEnum:
    if delta == 0:
        return const.CodeEnum.OK
    res = await client.coll.users.update_one(
        {"id": uid},
        {"$inc": {"usedSpace": delta}}
    )
    return const.CodeEnum.OK if res.modified_count == 1 else const.CodeEnum.OPERATION_FAILED


async def user_space_not_enough(au: tps.AuthedUser) -> bool:
    if config.is_local_db():
        return False
    return au.u.used_space > const.USER_TYPE.id2config(au.u.type).max_store_space


async def reset_password(uid: str, hashed: str) -> const.CodeEnum:
    res = await client.coll.users.update_one(
        {"id": uid},
        {"$set": {"hashed": hashed}}
    )
    return const.CodeEnum.OK if res.acknowledged == 1 else const.CodeEnum.OPERATION_FAILED
