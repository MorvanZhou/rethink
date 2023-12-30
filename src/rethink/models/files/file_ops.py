import hashlib
import io
import re
import zipfile
from os.path import normpath
from pathlib import Path
from platform import system
from typing import List, Tuple, BinaryIO, Dict, Union

from PIL import Image, UnidentifiedImageError
from bson.objectid import ObjectId
from fastapi import UploadFile
from qcloud_cos import CosConfig, CosServiceError, CosS3Client

from rethink import const, config
from rethink.models.database import COLL
from rethink.models.tps import UserFile
from rethink.models.user import update_used_space
from rethink.models.utils import short_uuid

INTERNAL_LINK_PTN = re.compile(r"\[\[(.*?)]]")
INTERNAL_IMG_PTN = re.compile(r"!\[\[(Pasted image .*?)]]")
INTERNAL_IMG_PTN2 = re.compile(r"!\[(.*?)]\((?!http)(.*?)\)")

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


def unzip_file(zip_bytes: bytes) -> Dict[str, Dict[str, Union[bytes, int]]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as ref:
        filepaths = ref.namelist()
        extracted_files = {}
        for filepath in filepaths:
            info = ref.getinfo(filepath)
            try:
                if system() in ["Darwin", "Linux"]:
                    _filepath = filepath.encode('cp437').decode('utf-8')
                elif system() == "Windows":
                    _filepath = filepath.encode('cp437').decode('gbk')
                else:
                    _filepath = filepath
            except UnicodeEncodeError:
                if system() == "Windows":
                    _filepath = filepath.encode("utf-8").decode("utf-8")
                _filepath = filepath
            sp = _filepath.split("/")
            if sp[0] in ["__MACOSX", ".DS_Store"]:
                continue
            if len(sp) > 1:
                _filepath = "/".join(sp[1:])
            if _filepath.strip() == "" or _filepath.startswith("."):
                continue

            # Check for directory traversal
            norm_path = normpath(_filepath)
            if norm_path.startswith('../') or norm_path.startswith('..\\'):
                continue  # or raise an exception

            extracted_files[_filepath] = {
                "file": ref.read(filepath),
                "size": info.file_size,
            }

    return extracted_files


async def __img_ptn_replace_upload(
        uid: str,
        filepath: str,
        filename: str,
        md: str,
        img_dict: Dict[str, bytes],
        resize_threshold: int,
        span: Tuple[int, int]
) -> str:
    """

    Args:
        filepath:
        filename:
        md:
        img_dict:
        resize_threshold:
        span:

    Returns:
        md, uploaded_file_size
    """
    if filepath not in img_dict:
        return md
    file = img_dict[filepath]
    ext = filepath.split(".")[-1].lower()
    if ext == "jpg":
        ext = "jpeg"
    content_type = f"image/{ext}"
    bio_file = io.BytesIO(file)
    bio_file.seek(0, io.SEEK_END)
    file_size_ = bio_file.tell()
    url = await __save_image(
        uid=uid,
        filename=filepath,
        file=bio_file,
        file_size=file_size_,
        content_type=content_type,
        resize_threshold=resize_threshold,
    )
    if url != "":
        md = f"{md[: span[0]]}![{filename}]({url}){md[span[1]:]}"
    return md


async def replace_inner_link_and_upload_image(
        uid: str,
        md: str,
        exist_filename2nid: Dict[str, str],
        img_path_dict: Dict[str, bytes],
        img_name_dict: Dict[str, bytes],
        resize_threshold: int,
) -> str:
    """

    Args:
        uid:
        md:
        exist_filename2nid:
        img_path_dict:
        img_name_dict:
        resize_threshold:

    Returns:
        md
    """
    # image
    for match in list(INTERNAL_IMG_PTN2.finditer(md))[::-1]:
        span = match.span()
        filename = match.group(1)
        filepath = match.group(2)
        md = await __img_ptn_replace_upload(
            uid=uid,
            filepath=filepath,
            filename=filename,
            md=md,
            img_dict=img_path_dict,
            resize_threshold=resize_threshold,
            span=span,
        )
    for match in list(INTERNAL_IMG_PTN.finditer(md))[::-1]:
        span = match.span()
        filepath = filename = match.group(1)
        md = await __img_ptn_replace_upload(
            uid=uid,
            filepath=filepath,
            filename=filename,
            md=md,
            img_dict=img_name_dict,
            resize_threshold=resize_threshold,
            span=span,
        )

    # node link
    for match in list(INTERNAL_LINK_PTN.finditer(md))[::-1]:
        span = match.span()
        filename = match.group(1)
        nid = exist_filename2nid.get(filename)
        if nid is None:
            nid = short_uuid()
            exist_filename2nid[filename] = nid
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
        content_type: str,
        file: BinaryIO,
        resize_threshold: int,
) -> BinaryIO:
    if file_size > resize_threshold:
        # reduce image size
        out = io.BytesIO()
        image = Image.open(file)
        image.save(out, format=content_type.split("/")[-1].upper(), quality=50, optimize=True)
    else:
        out = file
    out.seek(0)
    return out


async def __save_image(
        uid: str,
        filename: str,
        file: BinaryIO,
        file_size: int,
        content_type: str,
        resize_threshold: int,
) -> str:
    """

    Args:
        filename:
        file:
        file_size:
        content_type:
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
            content_type=content_type,
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
                content_type=content_type,
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
        url = await __save_image(
            uid=uid,
            filename=file.filename,
            file=file.file,
            file_size=file.size,
            content_type=file.content_type,
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
        content_type: str,
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
        content_type=content_type,
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
        ContentType=content_type,
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
        content_type: str,
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
            content_type=content_type,
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
