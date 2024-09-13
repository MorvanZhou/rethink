from collections import OrderedDict as OD
from datetime import datetime
from typing import List, Dict, Tuple, OrderedDict

from retk import const, config, regex, utils
from retk.core import scheduler
from retk.core.utils import cached_verification


class EmailServer:
    default_language = const.LanguageEnum.EN

    lang_subject = {
        const.LanguageEnum.EN.value: "Rethink: Security Code",
        const.LanguageEnum.ZH.value: "Rethink: 安全密码",
    }
    lang_template_id = {
        const.LanguageEnum.EN.value: 127743,
        const.LanguageEnum.ZH.value: 127744,
    }

    def send(self, recipient: str, numbers: str, expire: int, language: str) -> const.CodeEnum:
        try:
            subject = self.lang_subject[language]
            template_id = self.lang_template_id[language]
        except KeyError:
            subject = self.lang_subject[self.default_language]
            template_id = self.lang_template_id[self.default_language]

        return self._send(
            recipients=[recipient],
            subject=subject,
            template_id=template_id,
            values={"email": utils.mask_email(recipient), "numbers": numbers, "expire": expire},
        )

    @staticmethod
    def email_ok(email_addr: str) -> bool:
        if regex.EMAIL.fullmatch(email_addr) is None:
            return False
        return True

    def _send(self, recipients: List[str], subject: str, template_id: int, values: Dict) -> const.CodeEnum:
        for recipient in recipients:
            if not self.email_ok(recipient):
                return const.CodeEnum.INVALID_EMAIL
        conf = config.get_settings()

        _, code = scheduler.run_once_now(
            job_id=f"send_email_{conf.RETHINK_EMAIL}_{recipients}_{subject}_{template_id}_{values}",
            func=scheduler.tasks.email.send_verification_code,
            kwargs={
                "from_email": f"Rethink <{conf.RETHINK_EMAIL}>",
                "to_emails": recipients,
                "subject": subject,
                "values": values,
                "template_id": template_id,
                "secret_id": conf.RETHINK_EMAIL_SECRET_ID,
                "secret_key": conf.RETHINK_EMAIL_SECRET_KEY,
            },
        )
        return code


email_server = EmailServer()

cache_email: OrderedDict[str, Tuple[datetime, str]] = OD()


def encode_number(number: str, expired_min: int) -> str:
    return cached_verification.add_to_cache(
        cached=cache_email,
        code=number,
        expired_seconds=expired_min * 60
    )


def verify_number(cid: str, user_code: str) -> const.CodeEnum:
    return cached_verification.verify_captcha(
        cached=cache_email,
        cid=cid,
        user_code=user_code
    )
