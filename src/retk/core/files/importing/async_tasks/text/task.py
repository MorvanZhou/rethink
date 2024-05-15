from typing import List

import pymongo.errors

from retk import const, core
from retk.logger import logger
from retk.models.tps import AuthedUser, convert_user_dict_to_authed_user
from .. import utils


async def update_text_task(  # noqa: C901
        files: List[dict],
        max_file_size: int,
        uid: str,
        request_id: str,
):
    type_ = "md"
    await utils.import_set_modules()

    doc, finished = await utils.check_last_task_finished(uid=uid, type_=type_)
    if not finished:
        return

    for file in files:
        if not file["filename"].endswith(".md") and not file["filename"].endswith(".txt"):
            await utils.set_running_false(
                uid=uid,
                code=const.CodeEnum.INVALID_FILE_TYPE,
                msg=f"invalid file type: {file['filename']}",
            )
            return
        if file["size"] > max_file_size:
            await utils.set_running_false(
                uid=uid,
                code=const.CodeEnum.TOO_LARGE_FILE,
                msg=f"file size: {file['size']} > {max_file_size} (max file size): {file['filename']}",
            )
            return

    u, code = await core.user.get(uid=uid, disabled=False)
    au = AuthedUser(
        u=convert_user_dict_to_authed_user(u),
        request_id=request_id,
        language=u["settings"].get("language", const.LanguageEnum.EN.value),
    )
    for i, file in enumerate(files):
        try:
            md = file["content"].decode("utf-8")
        except (FileNotFoundError, OSError) as e:
            logger.error(f"error: {e}. filepath: {file['filename']}")
            await utils.set_running_false(
                uid=uid,
                code=const.CodeEnum.FILE_OPEN_ERROR,
                msg=f"file decode utf-8 failed, {e}: {file['filename']}",
            )
            return
        title = file["filename"].rsplit(".", 1)[0]
        md = title + "\n\n" + md
        try:
            _, code = await core.node.post(
                au=au,
                md=md,
                type_=const.NodeTypeEnum.MARKDOWN.value,
            )
        except pymongo.errors.DuplicateKeyError:
            continue
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"error: {e}. filepath: {file['filename']}")
            await utils.set_running_false(
                uid=uid,
                code=const.CodeEnum.FILE_OPEN_ERROR,
                msg=f"file decode utf-8 failed, {e}: {file['filename']}",
            )
            return
        if code != const.CodeEnum.OK:
            await utils.set_running_false(
                uid=uid,
                code=code,
                msg=f"file insert failed: {file['filename']}",
            )
            return
        if i % 20 == 0:
            doc, code = await utils.update_process(uid=uid, type_=type_, process=int(i / len(files) * 100))
            if code != const.CodeEnum.OK:
                await utils.set_running_false(
                    uid=uid,
                    code=code,
                    msg="uploading process update failed",
                )
                return
            if not doc["running"]:
                break

    await utils.finish_task(uid=uid)
