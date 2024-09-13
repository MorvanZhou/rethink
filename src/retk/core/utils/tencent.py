import hashlib
import hmac
from datetime import datetime
from typing import TypedDict

Headers = TypedDict("Headers", {
    "Authorization": str,
    "Content-Type": str,
    "Host": str,
    "X-TC-Action": str,
    "X-TC-Timestamp": str,
    "X-TC-Version": str,
    "X-TC-Language": str,
})


# 计算签名摘要函数
def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_auth(
        host: str,
        service: str,
        secret_id: str,
        secret_key: str,
        action: str,
        payload: bytes,
        timestamp: int,
        content_type: str,
) -> str:
    algorithm = "TC3-HMAC-SHA256"
    date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

    # ************* 步骤 1：拼接规范请求串 *************
    http_request_method = "POST"
    canonical_uri = "/"
    canonical_querystring = ""
    canonical_headers = f"content-type:{content_type}\nhost:{host}\nx-tc-action:{action.lower()}\n"
    signed_headers = "content-type;host;x-tc-action"
    hashed_request_payload = hashlib.sha256(payload).hexdigest()
    canonical_request = f"{http_request_method}\n" \
                        f"{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n" \
                        f"{signed_headers}\n{hashed_request_payload}"

    # ************* 步骤 2：拼接待签名字符串 *************
    credential_scope = f"{date}/{service}/tc3_request"
    hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"

    # ************* 步骤 3：计算签名 *************
    secret_date = sign(f"TC3{secret_key}".encode("utf-8"), date)
    secret_service = sign(secret_date, service)
    secret_signing = sign(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    # ************* 步骤 4：拼接 Authorization *************
    authorization = f"{algorithm}" \
                    f" Credential={secret_id}/{credential_scope}," \
                    f" SignedHeaders={signed_headers}," \
                    f" Signature={signature}"
    return authorization
