import asyncio
from datetime import datetime
from typing import Optional, BinaryIO, List, Dict

import httpx

try:
    from qcloud_cos import CosConfig, CosS3Client, CosServiceError, CosClientError
except ImportError:
    pass

from retk.config import get_settings
from retk.logger import logger


class COSClient:
    def __init__(self):
        self._client = None
        self.domain = None
        self.bucket = None

    def init(self):
        settings = get_settings()
        try:
            cos_conf = CosConfig(
                Region=settings.COS_REGION,
                SecretId=settings.COS_SECRET_ID,
                SecretKey=settings.COS_SECRET_KEY,
                Token=None,
                Domain=settings.COS_DOMAIN,
                Scheme='https',
            )
        except CosClientError:
            logger.info("COSClient | COS settings not found")
            raise ModuleNotFoundError("COS settings not found")
        self.domain = settings.COS_DOMAIN or f"{settings.COS_BUCKET_NAME}.cos.{settings.COS_REGION}.myqcloud.com"
        self.bucket = settings.COS_BUCKET_NAME
        self._client = CosS3Client(cos_conf)

    @staticmethod
    def get_user_data_key(
            uid: str,
            filename: str,
    ) -> str:
        return f"userData/{uid}/{filename}"

    def get_auth_headers(self, method: str, key: str) -> dict:
        auth_str = self._client.get_auth(
            Method=method.upper(),
            Bucket=self.bucket,
            Key=key,
        )
        headers = {
            "Authorization": auth_str,
            "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }
        return headers

    async def async_has_file(self, uid: str, filename: str) -> bool:
        key = self.get_user_data_key(uid=uid, filename=filename)
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.head(
                    url=f"https://{self.domain}/{key}",
                    headers=self.get_auth_headers("head", key),
                )
            except (
                    httpx.ConnectTimeout,
                    httpx.ConnectError,
                    httpx.ReadTimeout,
                    httpx.HTTPError
            ) as e:
                logger.error(f"has_file | error: {e}")
                return False
            if resp.status_code != 200:
                return False
        return True

    async def async_batch_has_file(self, uid: str, filenames: list[str]) -> dict[str, bool]:
        async def has_file(filename: str):
            return await self.async_has_file(uid=uid, filename=filename)

        tasks = [has_file(filename) for filename in filenames]
        results = await asyncio.gather(*tasks)
        return {filename: result for filename, result in zip(filenames, results)}

    def has_file(self, uid: str, filename: str) -> bool:
        try:
            _ = self._client.head_object(
                Bucket=self.bucket,
                Key=self.get_user_data_key(uid=uid, filename=filename)
            )
            return True
        except CosServiceError as e:
            if e.get_status_code() != 404:
                return True
        return False

    async def async_put(self, file: BinaryIO, uid: str, filename: str) -> bool:
        key = self.get_user_data_key(uid=uid, filename=filename)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    url=f"https://{self.domain}/{key}",
                    headers=self.get_auth_headers("put", key),
                    content=file.read(),
                )
            if resp.status_code != 200:
                logger.error(f"put_cos_object | error: {resp.text}")
                return False
        except (
                httpx.ConnectTimeout,
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.HTTPError
        ) as e:
            logger.error(f"put_cos_object | error: {e}")
            return False
        return True

    async def async_batch_put(self, uid: str, files: dict[str, BinaryIO]) -> dict[str, bool]:
        async def put_file(filename: str, file: BinaryIO):
            return await self.async_put(file=file, uid=uid, filename=filename)

        tasks = [put_file(filename, file) for filename, file in files.items()]
        batch_size = 5
        results = []
        for i in range(0, len(tasks), batch_size):
            results.extend(await asyncio.gather(*tasks[i:i + batch_size]))
        return {filename: result for filename, result in zip(files.keys(), results)}

    def put(self, file: BinaryIO, uid: str, filename: str) -> bool:
        try:
            _ = self._client.put_object(
                Bucket=self.bucket,
                Body=file,
                Key=self.get_user_data_key(uid=uid, filename=filename),
                StorageClass='STANDARD',  # 'STANDARD'|'STANDARD_IA'|'ARCHIVE',
                EnableMD5=False,
                # ContentType=content_type,
            )
        except CosServiceError as e:
            logger.error(f"failed to save file to cos: {e}")
            return False
        return True

    async def async_get(self, uid: str, filename: str) -> Optional[bytes]:
        key = self.get_user_data_key(uid=uid, filename=filename)
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    url=f"https://{self.domain}/{key}",
                    headers=self.get_auth_headers("get", key),
                )
            except (
                    httpx.ConnectTimeout,
                    httpx.ConnectError,
                    httpx.ReadTimeout,
                    httpx.HTTPError
            ) as e:
                logger.error(f"get_cos_object | error: {e}")
                return None
            if resp.status_code != 200:
                logger.error(f"get_cos_object | error: {resp.text}")
                return None
            return resp.content

    async def async_batch_get(self, uid: str, filenames: List[str]) -> Dict[str, bytes]:
        async def get_file(filename: str):
            return await self.async_get(uid=uid, filename=filename)

        tasks = [get_file(filename) for filename in filenames]
        batch_size = 5
        results = []
        for i in range(0, len(tasks), batch_size):
            results.extend(await asyncio.gather(*tasks[i:i + batch_size]))
        return {filename: result for filename, result in zip(filenames, results)}

    def get(self, uid: str, filename: str) -> Optional[bytes]:
        try:
            obj = self._client.get_object(
                Bucket=self.bucket,
                Key=self.get_user_data_key(uid=uid, filename=filename)
            )
        except CosServiceError as e:
            logger.error(f"failed to get file from cos: {e}")
            return None
        stream_body = obj["Body"]
        return stream_body.read()


cos_client = COSClient()
