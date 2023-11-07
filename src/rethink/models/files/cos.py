from qcloud_cos import CosConfig, CosServiceError, CosS3Client

from rethink import config

token = None
scheme = 'https'


def get_client() -> CosS3Client:
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


def upload_from_path(path: str):
    client = get_client()
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


def upload_from_bytes(b: bytes, filename: str, content_type: str) -> str:
    client = get_client()
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
        Body=b,
        Key=key,
        StorageClass='STANDARD',  # 'STANDARD'|'STANDARD_IA'|'ARCHIVE',
        EnableMD5=False,
        ContentType=content_type,
    )

    return url
