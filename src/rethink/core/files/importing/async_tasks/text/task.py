from typing import List

import pymongo.errors

from rethink import const, core
from rethink.logger import logger
from .. import utils


async def update_text_task(  # noqa: C901
        files: List[dict],
        max_file_size: int,
        uid: str,
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
                code=const.Code.INVALID_FILE_TYPE,
                msg=f"invalid file type: {file['filename']}",
            )
            return
        if file["size"] > max_file_size:
            await utils.set_running_false(
                uid=uid,
                code=const.Code.TOO_LARGE_FILE,
                msg=f"file size: {file['size']} > {max_file_size} (max file size): {file['filename']}",
            )
            return

    for i, file in enumerate(files):
        try:
            md = file["content"].decode("utf-8")
        except (FileNotFoundError, OSError) as e:
            logger.error(f"error: {e}. filepath: {file['filename']}")
            await utils.set_running_false(
                uid=uid,
                code=const.Code.FILE_OPEN_ERROR,
                msg=f"file decode utf-8 failed, {e}: {file['filename']}",
            )
            return
        title = file["filename"].rsplit(".", 1)[0]
        md = title + "\n\n" + md
        try:
            n, code = await core.node.post(
                uid=uid,
                md=md,
                type_=const.NodeType.MARKDOWN.value,
            )
        except pymongo.errors.DuplicateKeyError:
            continue
        except Exception as e:
            logger.error(f"error: {e}. filepath: {file['filename']}")
            await utils.set_running_false(
                uid=uid,
                code=const.Code.FILE_OPEN_ERROR,
                msg=f"file decode utf-8 failed, {e}: {file['filename']}",
            )
            return
        if code != const.Code.OK:
            await utils.set_running_false(
                uid=uid,
                code=code,
                msg=f"file insert failed: {file['filename']}",
            )
            return
        if i % 20 == 0:
            doc, code = await utils.update_process(uid=uid, type_=type_, process=int(i / len(files) * 100))
            if code != const.Code.OK:
                await utils.set_running_false(
                    uid=uid,
                    code=code,
                    msg="uploading process update failed",
                )
                return
            if not doc["running"]:
                break

    await utils.finish_task(uid=uid)
