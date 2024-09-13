import asyncio
import json
import time
from typing import Dict, List

import httpx

from retk.core.utils.tencent import get_auth


def send_verification_code(
        from_email: str,
        to_emails: List[str],
        subject: str,
        template_id: int,
        values: Dict,
        secret_id: str,
        secret_key: str,
):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(_send_verification_code(
        from_email=from_email,
        to_emails=to_emails,
        subject=subject,
        template_id=template_id,
        values=values,
        secret_id=secret_id,
        secret_key=secret_key,
    ))
    loop.close()
    return res


async def _send_verification_code(
        from_email: str,
        to_emails: List[str],
        subject: str,
        template_id: int,
        values: Dict,
        secret_id: str,
        secret_key: str,
):
    timestamp = int(time.time())
    payload = {
        "FromEmailAddress": from_email,
        "Destination": to_emails,
        "Template": {
            "TemplateID": template_id,
            "TemplateData": json.dumps(values)
        },
        "Subject": subject,
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    host = "ses.tencentcloudapi.com"
    action = "SendEmail"
    ct = "application/json"
    authorization = get_auth(
        host=host,
        service="ses",
        secret_id=secret_id,
        secret_key=secret_key,
        action="SendEmail",
        payload=payload_bytes,
        timestamp=timestamp,
        content_type=ct
    )
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=f"https://{host}",
            headers={
                "X-TC-Action": action,
                "X-TC-Region": "ap-hongkong",
                "X-TC-Version": "2020-10-02",
                "X-TC-Timestamp": str(timestamp),
                "Authorization": authorization,
                "Content-Type": ct,
            },
            content=payload_bytes,
        )
        print(response.status_code)
        print(response.text)
