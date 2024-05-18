import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

from bson.tz_util import utc
from pydantic_settings import BaseSettings
from qcloud_cos import CosConfig, CosServiceError, CosS3Client

from retk import config, const
from retk.logger import logger
from retk.models import tps
from retk.models.client import client


async def storage_md(node: tps.Node, keep_hist: bool) -> const.CodeEnum:  # noqa: C901
    nid = node["id"]
    md = node["md"]
    hist = node.get("history", [])
    date_format = "%Y-%m-%d %H:%M:%S.%fZ"

    if config.is_local_db():
        # save to local
        md_path = Path(
            config.get_settings().RETHINK_LOCAL_STORAGE_PATH
        ) / const.settings.DOT_DATA / "md" / (nid + ".md")
        md_path.write_text(md, encoding="utf-8")

    if not keep_hist:
        return const.CodeEnum.OK

    # ignore if the time difference is less than n minutes
    if len(hist) != 0:
        last_hist = hist[0]
        time = datetime.strptime(last_hist, date_format).replace(tzinfo=None)
        if (datetime.now(tz=utc).replace(tzinfo=None) - time) < timedelta(
                seconds=config.get_settings().MD_BACKUP_INTERVAL
        ):
            return const.CodeEnum.OK

    this_hist = node["modifiedAt"].strftime(date_format)
    hist.insert(0, this_hist)

    if config.is_local_db():
        md_dir = __get_md_hist_dir(nid)
        md_dir.mkdir(parents=True, exist_ok=True)
        filename = __windows_safe_path(this_hist)
        with open(md_dir / f"{filename}.md", "w", encoding="utf-8") as f:
            f.write(md)
    else:
        code = __save_md_to_cos(node["uid"], nid, this_hist, md)
        if code != const.CodeEnum.OK:
            return code

    if len(hist) > const.settings.MAX_MD_BACKUP_VERSIONS:
        drop = hist[-const.settings.MAX_MD_BACKUP_VERSIONS:]
        for h in drop:
            if config.is_local_db():
                md_dir = __get_md_hist_dir(nid)
                filename = __windows_safe_path(h)
                (md_dir / f"{filename}.md").unlink()
            else:
                __remove_md_from_cos(node["uid"], nid, h)
        hist = hist[:-const.settings.MAX_MD_BACKUP_VERSIONS]

    res = await client.coll.nodes.update_one(
        {"id": nid},
        {"$set": {"history": hist}}
    )
    if res.modified_count != 1:
        logger.error(f"failed to update node history: {nid}")
        return const.CodeEnum.OPERATION_FAILED
    return const.CodeEnum.OK


def delete_node_md(uid: str, nids: List[str]):
    if config.is_local_db():
        for nid in nids:
            dir_ = __get_md_hist_dir(nid)
            # remove dir even if it's not empty
            shutil.rmtree(dir_, ignore_errors=True)
            # remove current node md
            md_path = Path(
                config.get_settings().RETHINK_LOCAL_STORAGE_PATH
            ) / const.settings.DOT_DATA / "md" / (nid + ".md")
            md_path.unlink(missing_ok=True)
    else:
        for nid in nids:
            __remove_md_all_versions_from_cos(uid, nid)


def get_md(uid: str, nid: str, version: str) -> Tuple[str, const.CodeEnum]:
    if config.is_local_db():
        md_dir = __get_md_hist_dir(nid)
        filename = __windows_safe_path(version)
        with open(md_dir / f"{filename}.md", "r", encoding="utf-8") as f:
            md = f.read()
    else:
        md, code = __get_md_from_cos(uid, nid, version)
        if code != const.CodeEnum.OK:
            return "", code
    return md, const.CodeEnum.OK


def __windows_safe_path(filename: str) -> str:
    return filename.replace(":", "_").replace("\\", "_").replace("/", "_")


def __get_md_hist_dir(nid: str = None) -> Path:
    p = Path(config.get_settings().RETHINK_LOCAL_STORAGE_PATH) / const.settings.DOT_DATA / "md" / "hist"
    if nid is not None:
        p = p / nid
    return p


def __get_md_from_cos(uid: str, nid: str, version: str) -> Tuple[str, const.CodeEnum]:
    settings = config.get_settings()
    cos_client, key = __get_client_and_key(settings, uid, nid, version)

    try:
        res = cos_client.get_object(
            Bucket=settings.COS_BUCKET_NAME,
            Key=key,
        )
        md_body = b""
        while 1:
            chunk = res["Body"].read()
            if not chunk:
                break
            md_body += chunk
    except CosServiceError as e:
        logger.error(f"failed to get file from cos: {e}")
        return "", const.CodeEnum.COS_ERROR
    try:
        md = md_body.decode("utf-8")
    except UnicodeDecodeError as e:
        logger.error(f"failed to decode md: {e}. md: {md_body}")
        return "", const.CodeEnum.OPERATION_FAILED
    return md, const.CodeEnum.OK


def __save_md_to_cos(uid: str, nid: str, version: str, md: str) -> const.CodeEnum:
    settings = config.get_settings()
    cos_client, key, code = __cos_connect(settings, uid, nid, version)

    if code != const.CodeEnum.OK:
        return code

    # can raise error
    try:
        _ = cos_client.put_object(
            Bucket=settings.COS_BUCKET_NAME,
            Body=md.encode("utf-8"),
            Key=key,
            StorageClass='STANDARD',  # 'STANDARD'|'STANDARD_IA'|'ARCHIVE',
            EnableMD5=False,
            ContentType="text/markdown",
        )
    except CosServiceError as e:
        logger.error(f"failed to save file to cos: {e}")
        return const.CodeEnum.COS_ERROR
    return const.CodeEnum.OK


def __remove_md_from_cos(uid: str, nid: str, version: str) -> const.CodeEnum:
    settings = config.get_settings()
    cos_client, key, code = __cos_connect(settings, uid, nid, version, exist_ok=False)
    if code == const.CodeEnum.NODE_EXIST:
        try:
            _ = cos_client.delete_object(
                Bucket=settings.COS_BUCKET_NAME,
                Key=key
            )
        except CosServiceError as e:
            logger.error(f"failed to delete md from cos: {e}")
            return const.CodeEnum.COS_ERROR

    return const.CodeEnum.OK


def __remove_md_all_versions_from_cos(uid: str, nid: str) -> const.CodeEnum:
    settings = config.get_settings()
    cos_client, to_delete_dir = __get_client_and_key(settings, uid, nid)

    try:
        _ = cos_client.delete_object(
            Bucket=settings.COS_BUCKET_NAME,
            Key=to_delete_dir
        )
    except CosServiceError as e:
        logger.error(f"failed to delete md from cos: {e}")
        return const.CodeEnum.COS_ERROR

    return const.CodeEnum.OK


def __cos_connect(
        settings: BaseSettings,
        uid: str,
        nid: str,
        version: str,
        exist_ok: bool = False,
) -> Tuple[CosS3Client, str, const.CodeEnum]:
    cos_client, key = __get_client_and_key(settings, uid, nid, version)

    if not exist_ok:
        try:
            _ = cos_client.head_object(
                Bucket=settings.COS_BUCKET_NAME,
                Key=key
            )
            return cos_client, key, const.CodeEnum.NODE_EXIST
        except CosServiceError as e:
            if e.get_status_code() != 404:
                logger.error(f"failed to save md to cos: {e}")
                return cos_client, key, const.CodeEnum.COS_ERROR
    return cos_client, key, const.CodeEnum.OK


def __get_client_and_key(settings: BaseSettings, uid: str, nid: str, version: str = None) -> Tuple[CosS3Client, str]:
    cos_client = CosS3Client(
        CosConfig(
            Region=settings.COS_REGION,
            SecretId=settings.COS_SECRET_ID,
            SecretKey=settings.COS_SECRET_KEY,
            Token=None,
            Domain=None,
            Scheme='https',
        )
    )
    if version:
        key = f"mdHist/{uid}/{nid}/{version}.md"
    else:
        key = f"mdHist/{uid}/{nid}/"
    return cos_client, key
