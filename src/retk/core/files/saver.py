import hashlib
import io
from dataclasses import dataclass
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError
from bson import ObjectId

from retk.config import get_settings, is_local_db
from retk.const.app import FileTypesEnum
from retk.const.settings import IMG_RESIZE_THRESHOLD, DOT_DATA, LOCAL_FILE_URL_PRE_DIR
from retk.core.user import update_used_space
from retk.core.utils.cos import cos_client
from retk.logger import logger
from retk.models.client import client
from retk.models.tps import UserFile

RESIZE_IMAGE_TYPE = {".png", ".jpg", ".jpeg"}


@dataclass
class File:
    data: BinaryIO
    filename: str
    ext: str = ""

    def __post_init__(self):
        self.data.seek(0)
        md5_hash = hashlib.md5()
        for chunk in iter(lambda: self.data.read(4096), b""):
            md5_hash.update(chunk)
        self.data.seek(0)
        self.hash = md5_hash.hexdigest()

        if self.ext == "":
            sep = self.filename.rsplit(".", 1)
            self.ext = f".{sep[-1]}" if len(sep) > 1 else ""
        self.type = FileTypesEnum.get_type(self.ext)
        self.hashed_filename = f"{self.hash}{self.ext}"
        self._reset_size()

    def image_resize(self, resize_threshold: int):
        if self.type != FileTypesEnum.IMAGE or self.ext not in RESIZE_IMAGE_TYPE:
            return
        if self.ext.lower() == ".jpg":
            self.ext = ".jpeg"
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
            return f"/{LOCAL_FILE_URL_PRE_DIR}/{file.hashed_filename}"

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
        return f"/{LOCAL_FILE_URL_PRE_DIR}/{file.hashed_filename}"

    async def save_remote(self, uid: str, file: File):
        key = cos_client.get_user_data_key(uid=uid, filename=file.hashed_filename)
        url = f"https://{cos_client.domain}/{key}"

        doc = await client.coll.user_file.find_one({"uid": uid, "fid": file.hashed_filename})
        if doc:
            return url

        if await cos_client.async_has_file(uid=uid, filename=file.hashed_filename):
            return url

        if file.type == FileTypesEnum.IMAGE:
            file.image_resize(resize_threshold=self.resize_threshold)

        # can raise error
        if not await cos_client.async_put(
                file=file.data,
                uid=uid,
                filename=file.hashed_filename,
        ):
            return ""

        await add_to_db(uid=uid, file=file)
        return url


saver = Saver()
