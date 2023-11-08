import datetime
import hashlib
import io
import math
import os
import re
import uuid
from pathlib import Path
from typing import Tuple, Dict, BinaryIO

import jwt
import pypinyin
from PIL import Image, UnidentifiedImageError
from markdown import Markdown
from qcloud_cos import CosConfig, CosServiceError, CosS3Client

from rethink import config

HEADERS = {
    'typ': 'jwt',
    'alg': 'RS256'
}
alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
alphabet_len = len(alphabet)
__padding = int(math.ceil(math.log(2 ** 128, alphabet_len)))
__code_pattern = re.compile(r"^```[^\S\r\n]*[a-z]*?\n(.*?)\n```$", re.MULTILINE | re.DOTALL)


def short_uuid() -> str:
    """
    The output has the most significant digit first.
    """
    number = uuid.uuid4().int
    output = ""

    while number:
        number, digit = divmod(number, alphabet_len)
        output += alphabet[digit]
    if __padding:
        remainder = max(__padding - len(output), 0)
        output = output + alphabet[0] * remainder
    return output[::-1]


def __unmark_element(element, stream=None):
    if stream is None:
        stream = io.StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        __unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


# patching Markdown
Markdown.output_formats["plain"] = __unmark_element
__md = Markdown(output_format="plain")
__md.stripTopLevelTags = False


def md2txt(md: str) -> str:
    for found in list(__code_pattern.finditer(md))[::-1]:
        span = found.span()
        code = found.group(1)
        md = f"{md[: span[0]]}{code}{md[span[1]:]}"
    return __md.convert(md)


def preprocess_md(md: str) -> Tuple[str, str]:
    title, body = split_title_body(fulltext=md)
    title = md2txt(title.strip())
    body = body.strip()
    snippet = md2txt(md=body)[:200]
    return title, snippet


def txt2search_keys(txt: str) -> str:
    s1 = "".join(pypinyin.lazy_pinyin(txt))
    s2 = "".join(pypinyin.lazy_pinyin(txt, style=pypinyin.Style.BOPOMOFO))
    s = {s1, s2, txt}
    return " ".join(s).lower()


def split_title_body(fulltext: str) -> (str, str):
    title_body = fulltext.split("\n", maxsplit=1)
    title = title_body[0].strip()
    try:
        body = title_body[1].strip()
    except IndexError:
        body = ""
    return title, body


def jwt_encode(exp_delta: datetime.timedelta, data: dict) -> str:
    """
    Create token

    Args:
        exp_delta: expired delta
        data: payload data

    Returns:
        str: token
    """
    payload = {
        "exp": datetime.datetime.utcnow() + exp_delta
    }
    payload.update(data)
    token = jwt.encode(
        payload=payload,
        key=config.get_settings().JWT_KEY,
        algorithm=HEADERS["alg"],
        headers=HEADERS,
    )
    return token


def jwt_decode(token: str) -> dict:
    return jwt.decode(
        token,
        key=config.get_settings().JWT_KEY_PUB,
        algorithms=[HEADERS["alg"]],
        options={"verify_exp": True}
    )


INTERNAL_LINK_PTN = re.compile(r"\[\[(.*?)]]")
INTERNAL_IMG_PTN = re.compile(r"!\[\[(Pasted image .*?)]]")
INTERNAL_IMG_PTN2 = re.compile(r"!\[(.*?)]\((?!http)(.*?)\)")


def __img_ptn_replace_upload(
        filepath: str,
        filename: str,
        md: str,
        img_dict: Dict[str, bytes],
        min_img_size: int,
        span: Tuple[int, int]
):
    if filepath not in img_dict:
        return md
    file = img_dict[filepath]
    ext = filepath.split(".")[-1].lower()
    if ext == "jpg":
        ext = "jpeg"
    content_type = f"image/{ext}"
    url, code = save_image(
        filename=filepath,
        file=io.BytesIO(file),
        file_size=len(file),
        content_type=content_type,
        min_img_size=min_img_size,
    )
    if code == 0:
        md = f"{md[: span[0]]}![{filename}]({url}){md[span[1]:]}"
    return md


def replace_inner_link(
        md: str,
        exist_filename2nid: Dict[str, str],
        img_path_dict: Dict[str, bytes],
        img_name_dict: Dict[str, bytes],
        min_img_size: int,
) -> str:
    # image
    for match in list(INTERNAL_IMG_PTN2.finditer(md))[::-1]:
        span = match.span()
        filename = match.group(1)
        filepath = match.group(2)
        md = __img_ptn_replace_upload(
            filepath=filepath,
            filename=filename,
            md=md,
            img_dict=img_path_dict,
            min_img_size=min_img_size,
            span=span,
        )
    for match in list(INTERNAL_IMG_PTN.finditer(md))[::-1]:
        span = match.span()
        filepath = filename = match.group(1)
        md = __img_ptn_replace_upload(
            filepath=filepath,
            filename=filename,
            md=md,
            img_dict=img_name_dict,
            min_img_size=min_img_size,
            span=span,
        )

    # link
    for match in list(INTERNAL_LINK_PTN.finditer(md))[::-1]:
        span = match.span()
        filename = match.group(1)
        nid = exist_filename2nid.get(filename)
        if nid is None:
            nid = short_uuid()
            exist_filename2nid[filename] = nid
        md = f"{md[: span[0]]}[@{filename}](/n/{nid}){md[span[1]:]}"
    return md


def change_link_title(md: str, nid: str, new_title: str) -> str:
    new_md = re.sub(
        r"\[@[^].]*?]\(/n/{}/?\)".format(nid),
        f"[@{new_title}](/n/{nid})",
        md,
    )
    return new_md


def file_hash(file: BinaryIO) -> str:
    # https://stackoverflow.com/questions/22058048/hashing-a-file-in-python
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
        min_img_size: int,
) -> BinaryIO:
    if file_size > min_img_size:
        # reduce image size
        out = io.BytesIO()
        image = Image.open(file)
        image.save(out, format=content_type.split("/")[-1].upper(), quality=50, optimize=True)
        out.seek(0)
    else:
        out = file
    return out


def save_image(
        filename: str,
        file: BinaryIO,
        file_size: int,
        content_type: str,
        min_img_size: int,
) -> Tuple[str, int]:
    fn = Path(filename)
    ext = fn.suffix.lower()
    hashed = file_hash(file)

    if config.is_local_db():
        host = os.environ["VUE_APP_API_HOST"]
        port = os.environ["VUE_APP_API_PORT"]
        if not host.startswith("http"):
            host = "http://" + host
        # upload to local storage
        img_dir = config.get_settings().LOCAL_STORAGE_PATH / ".data" / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        img_path = img_dir / (hashed + ext)
        if img_path.exists():
            # skip the same image
            return f"{host}:{port}/i/{img_path.name}", 0

        try:
            out_bytes = __get_out_bytes(
                file_size=file_size,
                content_type=content_type,
                file=file,
                min_img_size=min_img_size
            )
            Image.open(out_bytes).save(img_path)
        except (
                FileNotFoundError,
                OSError,
                UnidentifiedImageError,
                ValueError,
                TypeError,
        ):
            return filename, 1

        return f"{host}:{port}/i/{img_path.name}", 0
    else:
        # upload to cos
        try:
            url = upload_bytes_to_cos(
                file_size=file_size,
                content_type=content_type,
                file=file,
                min_img_size=min_img_size,
                filename=hashed + ext,
            )
        except CosServiceError:
            return filename, 1

        return url, 0


def __get_cos_client() -> CosS3Client:
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
    return CosS3Client(cos_conf)


def upload_path_to_cos(path: str):
    client = __get_cos_client()
    settings = config.get_settings()
    with open(path, "rb") as fp:
        filename = path.split("/")[-1]
        key = f"{settings.COS_KEY_PREFIX}/user/img/{filename}"
        response = client.put_object(
            Bucket=settings.COS_BUCKET_NAME,
            Body=fp,
            Key=key,
            StorageClass='STANDARD',  # 'STANDARD'|'STANDARD_IA'|'ARCHIVE',
            # ContentType="",
            EnableMD5=False
        )
        print(response['ETag'])


def upload_bytes_to_cos(
        file_size: int,
        content_type: str,
        file: BinaryIO,
        min_img_size: int,
        filename: str) -> str:
    client = __get_cos_client()
    settings = config.get_settings()
    key = f"{settings.COS_KEY_PREFIX}/user/img/{filename}"

    url = f"https://{settings.COS_BUCKET_NAME}.cos.{settings.COS_REGION}.myqcloud.com/{key}"

    try:
        _ = client.head_object(
            Bucket=settings.COS_BUCKET_NAME,
            Key=key
        )
        return url
    except CosServiceError as e:
        if e.get_status_code() != 404:
            return url

    # can raise error
    _ = client.put_object(
        Bucket=settings.COS_BUCKET_NAME,
        Body=__get_out_bytes(
            file_size=file_size,
            content_type=content_type,
            file=file,
            min_img_size=min_img_size
        ),
        Key=key,
        StorageClass='STANDARD',  # 'STANDARD'|'STANDARD_IA'|'ARCHIVE',
        EnableMD5=False,
        ContentType=content_type,
    )

    return url
