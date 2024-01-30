import hashlib
import io
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from os.path import normpath
from pathlib import Path
from typing import List, Tuple, BinaryIO, Dict, Optional

from PIL import Image, UnidentifiedImageError
from bson.objectid import ObjectId
from fastapi import UploadFile
from qcloud_cos import CosConfig, CosServiceError, CosS3Client

from rethink import const, config, regex
from rethink.core.user import update_used_space
from rethink.models.database import COLL
from rethink.models.tps import UserFile
from rethink.utils import short_uuid

VALID_IMG_EXT = {"jpg", "jpeg", "png", "gif", "svg"}


async def delete_file(uid: str, fid: str) -> const.Code:
    success_deletion, failed_deletion = await delete_files(uid=uid, fids=[fid])
    if len(success_deletion) != 1:
        return const.Code.OPERATION_FAILED
    return const.Code.OK


async def delete_files(uid: str, fids: List[str]) -> Tuple[List[str], List[str]]:
    success_deletion = []
    failed_deletion = []
    delta = 0
    for fid in fids:
        doc = await COLL.user_file.find_one_and_delete({"uid": uid, "fid": fid})
        if doc is None:
            failed_deletion.append(fid)
        else:
            success_deletion.append(fid)
            delta -= doc["size"]

    await update_used_space(uid=uid, delta=delta)
    return success_deletion, failed_deletion


def _decode_filename(filepath: str) -> str:
    # 尝试使用不同的编码格式解码文件名
    encodings = ['utf-8', 'gbk', 'cp437']
    for encoding in encodings:
        try:
            return filepath.encode('cp437').decode(encoding)
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue
    return filepath


@dataclass
class UnzipObsidian:
    @dataclass
    class Meta:
        __slots__ = ["filepath", "filename", "title", "file", "size", "duplicate", "created_at"]
        filepath: str
        filename: str
        title: str
        file: bytes
        size: int
        duplicate: bool
        created_at: Optional[datetime]

    md: Dict[str, Meta] = field(default_factory=dict)
    md_full: Dict[str, Meta] = field(default_factory=dict)
    others: Dict[str, Meta] = field(default_factory=dict)
    others_full: Dict[str, Meta] = field(default_factory=dict)


def unzip_obsidian(zip_bytes: bytes) -> UnzipObsidian:
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        filepaths = zf.namelist()
        extracted_files = UnzipObsidian()
        for filepath in filepaths:
            info = zf.getinfo(filepath)
            if info.is_dir():
                continue
            try:
                _filepath = _decode_filename(filepath)
            except UnicodeDecodeError:
                _filepath = filepath
            fp = Path(_filepath.split("/", 1)[-1])
            # filter out system files
            has_invalid_suffix = False
            for p in fp.parts:
                if p.startswith(".") or fp.name.startswith("__MACOSX"):
                    has_invalid_suffix = True
                    break
            if has_invalid_suffix:
                continue

            # Check for directory traversal
            norm_path = normpath(fp)
            if norm_path.startswith('../') or norm_path.startswith('..\\'):
                continue  # or raise an exception
            try:
                title = regex.MD_FILE_EXT.findall(fp.name)[0]
            except IndexError:
                title = fp.name

            meta = UnzipObsidian.Meta(
                filepath=norm_path,
                filename=fp.name,
                title=title,
                file=zf.read(filepath),
                size=info.file_size,
                duplicate=False,
                created_at=datetime(*info.date_time),
            )

            if fp.suffix.lower() == ".md":
                entry = extracted_files.md
                entry_full = extracted_files.md_full
            else:
                entry = extracted_files.others
                entry_full = extracted_files.others_full

            if fp.name in entry:
                meta.duplicate = True
            else:
                entry[fp.name] = meta
            entry_full[str(fp)] = meta

    return extracted_files


async def __file_ptn_replace_upload(
        uid: str,
        filepath: str,
        filename: str,  # with ext
        md: str,
        others_full: Dict[str, UnzipObsidian.Meta],
        others_name: Dict[str, UnzipObsidian.Meta],
        resize_threshold: int,
        span: Tuple[int, int]
) -> str:
    """

    Args:
        filepath:
        filename:
        md:
        others_full:
        others_name:
        resize_threshold:
        span:

    Returns:
        md, uploaded_file_size
    """
    try:
        meta = others_name[filename]
    except KeyError:
        try:
            meta = others_full[filepath]
        except KeyError:
            # not inner file
            return md

    # ext = filepath.split(".")[-1].lower()
    # if ext == "jpg":
    #     ext = "jpeg"
    # content_type = f"image/{ext}"
    bio_file = io.BytesIO(meta.file)
    bio_file.seek(0, io.SEEK_END)
    file_size_ = bio_file.tell()
    url = await __save_file(
        uid=uid,
        filename=meta.filename,
        file=bio_file,
        file_size=file_size_,
        resize_threshold=resize_threshold,
    )
    if url != "":
        md = f"{md[: span[0]]}![{filename}]({url}){md[span[1]:]}"
    return md


async def replace_inner_link_and_upload(
        uid: str,
        md: str,
        exist_path2nid: Dict[str, str],
        others_full: Dict[str, UnzipObsidian.Meta],
        others_name: Dict[str, UnzipObsidian.Meta],
        resize_threshold: int,
) -> str:
    """

    Args:
        uid:
        md:
        exist_path2nid:
        others_full:
        others_name:
        resize_threshold:

    Returns:
        md
    """
    # orig image link to inner image file
    for match in list(regex.MD_IMG.finditer(md))[::-1]:
        span = match.span()
        filename = match.group(1)
        filepath = match.group(2)

        # ![xxx](aa/bb/cc.png)
        md = await __file_ptn_replace_upload(
            uid=uid,
            filepath=filepath,  # full path in zip
            filename=filename,  # filename in md
            md=md,
            others_full=others_full,
            others_name=others_name,
            resize_threshold=resize_threshold,
            span=span,
        )

    # files
    for match in list(regex.OBS_INTERNAL_FILE.finditer(md))[::-1]:
        span = match.span()
        filepath = match.group(1)

        # ![[aa/bb/cc.png]]
        # ![[aa.pdf]]
        md = await __file_ptn_replace_upload(
            uid=uid,
            filepath=filepath,
            filename=Path(filepath).name,
            md=md,
            others_full=others_full,
            others_name=others_name,
            resize_threshold=resize_threshold,
            span=span,
        )

    # node link
    for match in list(regex.OBS_INTERNAL_LINK.finditer(md))[::-1]:
        span = match.span()
        filename = match.group(1)
        path = f"{filename}.md"
        try:
            nid = exist_path2nid[path]
        except KeyError:
            nid = short_uuid()
            exist_path2nid[path] = nid
        md = f"{md[: span[0]]}[@{filename}](/n/{nid}){md[span[1]:]}"
    return md


def file_hash(file: BinaryIO) -> str:
    md5_hash = hashlib.md5()
    file.seek(0)
    for chunk in iter(lambda: file.read(4096), b""):
        md5_hash.update(chunk)
    file.seek(0)
    return md5_hash.hexdigest()


def __get_out_bytes(
        file_size: int,
        file: BinaryIO,
        resize_threshold: int,
) -> BinaryIO:
    if file_size > resize_threshold:
        # reduce image size
        out = io.BytesIO()
        image = Image.open(file)
        image.save(out, format="PNG", quality=50, optimize=True)
    else:
        out = file
    out.seek(0)
    return out


async def __save_file(
        uid: str,
        filename: str,
        file: BinaryIO,
        file_size: int,
        resize_threshold: int,
) -> str:
    """

    Args:
        filename:
        file:
        file_size:
        resize_threshold:

    Returns:
        url
    """
    fn = Path(filename)
    ext = fn.suffix.lower()
    hashed = file_hash(file)

    if config.is_local_db():
        url = await upload_to_local_storage(
            uid=uid,
            file_size=file_size,
            file=file,
            resize_threshold=resize_threshold,
            filename=filename,
            fid=hashed + ext,
        )

    else:
        # upload to cos
        try:
            url = await upload_bytes_to_cos(
                uid=uid,
                file_size=file_size,
                file=file,
                resize_threshold=resize_threshold,
                filename=filename,
                fid=hashed + ext,
            )
        except CosServiceError:
            return ""

    return url


async def save_upload_files(
        uid: str,
        files: List[UploadFile],
        max_image_size: int,
        resize_threshold: int,
) -> dict:
    res = {
        "errFiles": [],
        "succMap": {},
        "code": const.Code.OK,
    }
    for file in files:
        filename = file.filename
        # validate MIME image type
        if not file.content_type.startswith("image/"):
            res["errFiles"].append(filename)
            continue
        if file.size > max_image_size:
            res["errFiles"].append(filename)
            continue
        url = await __save_file(
            uid=uid,
            filename=file.filename,
            file=file.file,
            file_size=file.size,
            resize_threshold=resize_threshold,
        )
        if url == "":
            res["errFiles"].append(filename)
            continue
        res["succMap"][filename] = url
    return res


async def upload_bytes_to_cos(
        uid: str,
        file_size: int,
        file: BinaryIO,
        resize_threshold: int,
        filename: str,
        fid: str,
) -> str:
    token = None
    scheme = 'https'

    settings = config.get_settings()
    secret_id = settings.COS_SECRET_ID
    secret_key = settings.COS_SECRET_KEY
    region = settings.COS_REGION
    domain = None
    cos_conf = CosConfig(
        Region=region,
        SecretId=secret_id,
        SecretKey=secret_key,
        Token=token,
        Domain=domain,
        Scheme=scheme,
    )
    client = CosS3Client(cos_conf)

    settings = config.get_settings()
    key = f"userData/{uid}/{fid}"

    url = f"https://{settings.COS_BUCKET_NAME}.cos.{settings.COS_REGION}.myqcloud.com/{key}"

    doc = await COLL.user_file.find_one({"uid": uid, "fid": fid})
    if doc:
        return url

    try:
        _ = client.head_object(
            Bucket=settings.COS_BUCKET_NAME,
            Key=key
        )
        return url
    except CosServiceError as e:
        if e.get_status_code() != 404:
            return url
    body = __get_out_bytes(
        file_size=file_size,
        file=file,
        resize_threshold=resize_threshold
    )
    # can raise error
    _ = client.put_object(
        Bucket=settings.COS_BUCKET_NAME,
        Body=body,
        Key=key,
        StorageClass='STANDARD',  # 'STANDARD'|'STANDARD_IA'|'ARCHIVE',
        EnableMD5=False,
        # ContentType=content_type,
    )
    await insert_new_file(
        uid=uid,
        fid=fid,
        filename=filename,
        file_size=body.tell(),
    )
    return url


async def upload_to_local_storage(
        uid: str,
        file_size: int,
        file: BinaryIO,
        resize_threshold: int,
        filename: str,
        fid: str,
) -> str:
    # upload to local storage
    img_path = config.get_settings().LOCAL_STORAGE_PATH / ".data" / "files" / fid
    img_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"/files/{fid}"
    if img_path.exists():
        # skip the same image
        return url
    try:
        out_bytes = __get_out_bytes(
            file_size=file_size,
            file=file,
            resize_threshold=resize_threshold
        )
        Image.open(out_bytes).save(img_path)
    except (
            FileNotFoundError,
            OSError,
            UnidentifiedImageError,
            ValueError,
            TypeError,
    ):
        return ""
    # point move to the end
    out_bytes.seek(0, io.SEEK_END)
    size = out_bytes.tell()
    await insert_new_file(
        uid=uid,
        fid=fid,
        filename=filename,
        file_size=size,
    )
    return url


async def insert_new_file(
        uid: str,
        fid: str,
        filename: str,
        file_size: int,
):
    doc: UserFile = {
        "_id": ObjectId(),
        "uid": uid,
        "fid": fid,
        "filename": filename,
        "size": file_size,
    }
    await COLL.user_file.insert_one(doc)
    await update_used_space(uid=uid, delta=file_size)
