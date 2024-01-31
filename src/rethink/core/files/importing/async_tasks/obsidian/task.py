import time
import zipfile

import pymongo.errors

from rethink import const, core
from rethink.logger import logger
from . import ops
from .. import utils


async def upload_obsidian_task(  # noqa: C901
        bytes_data: bytes,
        filename: str,
        max_file_size: int,
        uid: str,
) -> None:
    type_ = "obsidian"
    await utils.import_set_modules()

    doc, finished = await utils.check_last_task_finished(uid=uid, type_=type_)
    if not finished:
        return

    t0 = time.time()
    try:
        unzipped_files = ops.unzip_obsidian(bytes_data)
    except zipfile.BadZipFile as e:
        await utils.set_running_false(
            uid,
            const.Code.INVALID_FILE_TYPE,
            msg=f"unzip failed: {e}"
        )
        logger.info(f"invalid file type: {filename}, uid: {uid}")
        return
    t1 = time.time()
    logger.info(f"obsidian upload, uid={uid}, unzip time: {t1 - t0:.2f}")

    existed_path2nid = doc.get("obsidian", {}).copy()
    md_count = len(unzipped_files.md_full)
    if md_count == 0:
        await utils.set_running_false(
            uid,
            const.Code.INVALID_FILE_TYPE,
            msg="no md file found",
        )
        logger.info(f"no md file found, uid: {uid}")
        return
    elif md_count > 2000:
        await utils.set_running_false(
            uid,
            const.Code.TOO_MANY_FILES,
            msg=f"md file count: {md_count} > 2000",
        )
        logger.info(f"too many md files: {md_count}, uid: {uid}")
        return

    # check file size
    for full in [unzipped_files.md_full, unzipped_files.others_full]:
        for full_path, meta in full.items():
            meta: ops.UnzipObsidian.Meta

            if meta.size > max_file_size:
                await utils.set_running_false(
                    uid,
                    const.Code.TOO_LARGE_FILE,
                    msg=f"file size > {max_file_size}: {full_path}",
                )
                logger.info(f"too large file: {full_path}, uid: {uid}")
                return

    t2 = time.time()
    logger.info(f"obsidian upload, uid={uid}, filter time: {t2 - t1:.2f}")

    # add new md files with only title
    for i, (full_path, meta) in enumerate(unzipped_files.md_full.items()):
        meta: ops.UnzipObsidian.Meta

        if full_path in existed_path2nid:
            continue

        try:
            n, code = await core.node.add(
                uid=uid,
                md=meta.title,
                type_=const.NodeType.MARKDOWN.value,
            )
        except pymongo.errors.DuplicateKeyError:
            logger.error(f"duplicate key: {full_path}, uid: {uid}")
            continue
        if code != const.Code.OK:
            await utils.set_running_false(
                uid,
                code,
                msg=f"new file insert failed: {full_path}",
            )
            logger.error(f"error: {code}, filepath: {full_path}, uid: {uid}")
            return

        # add full path and short name to existed_path2nid
        existed_path2nid[full_path] = n["id"]
        if meta.filename not in existed_path2nid:
            existed_path2nid[meta.filename] = n["id"]
        if i % 20 == 0:
            doc, code = await utils.update_process(uid=uid, type_=type_, process=int(i / md_count * 10))
            if code != const.Code.OK:
                await utils.set_running_false(
                    uid,
                    code,
                    msg="process updating failed",
                )
                logger.info(f"error: {code}, filepath: {full_path}, uid: {uid}")
                return
            if not doc["running"]:
                break
    t3 = time.time()
    logger.info(f"obsidian upload, uid={uid}, add new md time: {t3 - t2:.2f}")

    # update all md content and update md files
    for i, (full_path, meta) in enumerate(unzipped_files.md_full.items()):
        meta: ops.UnzipObsidian.Meta

        try:
            md = meta.file.decode("utf-8")
        except (FileNotFoundError, OSError, UnicodeDecodeError) as e:
            logger.error(f"error: {e}. filepath: {full_path}")
            await utils.set_running_false(
                uid,
                const.Code.FILE_OPEN_ERROR,
                msg=f"file decode utf-8 failed, {e}: {full_path}",
            )
            logger.info(f"error: {const.Code.FILE_OPEN_ERROR}, filepath: {full_path}, uid: {uid}")
            return

        md = await ops.replace_inner_link_and_upload(
            uid=uid,
            md=md,
            exist_path2nid=existed_path2nid,
            others_full=unzipped_files.others_full,
            others_name=unzipped_files.others,
        )
        md = meta.title + "\n\n" + md
        nid = existed_path2nid[full_path]
        n, code = await core.node.update(
            uid=uid,
            nid=nid,
            md=md,
            refresh_on_same_md=True,
        )
        if code == const.Code.NODE_NOT_EXIST:
            n, code = await core.node.add(
                uid=uid,
                md=md,
                type_=const.NodeType.MARKDOWN.value,
            )
            if code != const.Code.OK:
                await utils.set_running_false(
                    uid,
                    code,
                    msg=f"file insert failed: {full_path}",
                )
                logger.info(f"error: {code}, filepath: {full_path}, uid: {uid}")
                return
            existed_path2nid[full_path] = n["id"]
        elif code != const.Code.OK:
            await utils.set_running_false(
                uid,
                code,
                msg=f"file updating failed: {full_path}",
            )
            logger.info(f"error: {code}, filepath: {full_path}, uid: {uid}")
            return
        if i % 20 == 0:
            doc, code = await utils.update_process(uid=uid, type_=type_, process=int(i / md_count * 80 + 10))
            if code != const.Code.OK:
                await utils.set_running_false(
                    uid,
                    code,
                    msg="uploading process update failed",
                )
                logger.info(f"error: {code}, filepath: {full_path}, uid: {uid}")
                return
            if not doc["running"]:
                break
    t4 = time.time()
    logger.info(f"obsidian upload, uid={uid}, update all files time: {t4 - t3:.2f}")

    # update for old obsidian files
    count = 0
    for base_name, nid in doc["obsidian"].items():
        if base_name not in existed_path2nid:
            n, code = await core.node.get(uid=uid, nid=nid)
            if code != const.Code.OK:
                continue
            n, code = await core.node.update(
                uid=uid,
                nid=nid,
                md=n["md"],
                refresh_on_same_md=True,
            )
            if code != const.Code.OK:
                continue
        if count % 20 == 0:
            doc, code = await utils.update_process(
                uid=uid, type_=type_, process=int(count / len(doc["obsidian"]) * 10 + 90))
            if code != const.Code.OK:
                await utils.set_running_false(
                    uid,
                    code,
                    msg="uploading process update failed",
                )
                logger.info(f"error: {code}, uid: {uid}")
                return
            if not doc["running"]:
                break

        count += 1

    t5 = time.time()
    logger.info(f"obsidian upload, uid={uid}, update for old obsidian files time: {t5 - t4:.2f}")

    await utils.finish_task(uid=uid, obsidian=existed_path2nid)
