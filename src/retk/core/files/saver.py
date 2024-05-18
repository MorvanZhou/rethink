import hashlib
import io
from dataclasses import dataclass
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError
from bson import ObjectId
from qcloud_cos import CosConfig, CosServiceError, CosS3Client

from retk.config import get_settings, is_local_db
from retk.const.app import FileTypesEnum
from retk.const.settings import IMG_RESIZE_THRESHOLD, DOT_DATA
from retk.core.user import update_used_space
from retk.logger import logger
from retk.models.client import client
from retk.models.tps import UserFile


@dataclass
class File:
    data: BinaryIO
    filename: str

    def __post_init__(self):
        self.data.seek(0)
        md5_hash = hashlib.md5()
        for chunk in iter(lambda: self.data.read(4096), b""):
            md5_hash.update(chunk)
        self.data.seek(0)
        self.hash = md5_hash.hexdigest()
        sep = self.filename.rsplit(".", 1)
        self.ext = f".{sep[-1]}" if len(sep) > 1 else ""
        self.type = FileTypesEnum.get_type(self.ext)
        self.hashed_filename = f"{self.hash}{self.ext}"
        self._reset_size()

    def image_resize(self, resize_threshold: int):
        if self.type != FileTypesEnum.IMAGE:
            return
        if self.size > resize_threshold:
            # reduce image size
            out = io.BytesIO()
            image = Image.open(self.data)
            image.save(out, format=self.ext.upper()[1:], quality=50, optimize=True)
            self.data = out
        self._reset_size()

    def _reset_size(self):
        self.data.seek(0, io.SEEK_END)
        self.size = self.data.tell()
        self.data.seek(0)

    def is_unknown_type(self):
        return self.type == FileTypesEnum.UNKNOWN


async def add_to_db(
        uid: str,
        file: File,
):
    doc: UserFile = {
        "_id": ObjectId(),
        "uid": uid,
        "fid": file.hash,
        "filename": file.filename,
        "size": file.size,
    }
    await client.coll.user_file.insert_one(doc)
    await update_used_space(uid=uid, delta=file.size)


class Saver:
    resize_threshold = IMG_RESIZE_THRESHOLD

    async def save(self, uid: str, file: File):
        if is_local_db():
            url = await self.save_local(uid=uid, file=file)
        else:
            url = await self.save_remote(uid=uid, file=file)
        return url

    async def save_local(self, uid: str, file: File) -> str:
        path = get_settings().RETHINK_LOCAL_STORAGE_PATH / DOT_DATA / "files" / file.hashed_filename
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            # skip the same image
            return f"/files/{file.hashed_filename}"

        try:
            if file.type == FileTypesEnum.IMAGE:
                file.image_resize(resize_threshold=self.resize_threshold)
                Image.open(file.data).save(path)
            else:
                with open(path, "wb") as f:
                    f.write(file.data.read())
        except (
                FileNotFoundError,
                OSError,
                UnidentifiedImageError,
                ValueError,
                TypeError,
        ) as e:
            logger.error(f"failed to save file: {file.filename}. {e}")
            return ""

        await add_to_db(uid=uid, file=file)
        return f"/files/{file.hashed_filename}"

    async def save_remote(self, uid: str, file: File):
        # to cos
        token = None

        settings = get_settings()
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
            Scheme='https',
        )
        cos_client = CosS3Client(cos_conf)

        key = f"userData/{uid}/{file.hashed_filename}"

        url = f"https://{settings.COS_BUCKET_NAME}.cos.{settings.COS_REGION}.myqcloud.com/{key}"

        doc = await client.coll.user_file.find_one({"uid": uid, "fid": file.hashed_filename})
        if doc:
            return url

        try:
            _ = cos_client.head_object(
                Bucket=settings.COS_BUCKET_NAME,
                Key=key
            )
            return url
        except CosServiceError as e:
            if e.get_status_code() != 404:
                return url

        if file.type == FileTypesEnum.IMAGE:
            file.image_resize(resize_threshold=self.resize_threshold)

        # can raise error
        try:
            _ = cos_client.put_object(
                Bucket=settings.COS_BUCKET_NAME,
                Body=file.data,
                Key=key,
                StorageClass='STANDARD',  # 'STANDARD'|'STANDARD_IA'|'ARCHIVE',
                EnableMD5=False,
                # ContentType=content_type,
            )
        except CosServiceError as e:
            logger.error(f"failed to save file to cos: {e}")
            return ""
        await add_to_db(uid=uid, file=file)
        return url


saver = Saver()
