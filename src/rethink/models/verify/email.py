import email.header
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from textwrap import dedent
from typing import List

from rethink import const, config


class EmailServer:
    default_language = const.Language.EN

    lang_register_subject = {
        const.Language.EN: "Rethink: Register",
        const.Language.ZH: "Rethink: 注册",
    }

    lang_register_content = {
        const.Language.EN: dedent("""\
        Hi!<br><br>
        Welcome to Rethink, your verification code is:
        <br><br>
        <strong>{code}</strong>
        <br><br>
        Valid for 5 minutes, please complete the registration process as soon as possible.
        <br><br>
        Thank you!<br>
        Rethink Team
        """),
        const.Language.ZH: dedent("""\
        您好!
        <br><br>
        欢迎来到 Rethink，你的验证信息是：
        <br><br>
        <strong>{code}</strong>
        <br><br>
        此验证信息在 5 分钟内有效，请尽快完成注册流程。
        <br><br>
        谢谢！<br>
        Rethink 团队
        """),
    }

    lang_reset_pwd_subject = {
        const.Language.EN: "Rethink: Reset Password",
        const.Language.ZH: "Rethink: 重置密码",
    }
    lang_reset_pwd_content = {
        const.Language.EN: dedent("""\
        Your verification code for Rethink reset password is:
        <br><br>
        <strong>{numbers}</strong>
        <br><br>
        Valid for {expire} minutes, please do not tell others to prevent personal information leakage.
        <br><br>
        If you did not apply for a password reset, please ignore this email.
        <br><br>
        Thank you!<br>
        Rethink Team
        """),
        const.Language.ZH: dedent("""\
        您的 Rethink 重置密码所需的验证码为：
        <br><br>
        <strong>{numbers}</strong>
        <br><br>
        有效期 {expire} 分钟，请勿告知他人，以防个人信息泄露。
        <br><br>
        如果您没有申请重置密码，请忽略此邮件。
        <br><br>
        谢谢！<br>
        Rethink 团队
        """),
    }

    def __init__(self):
        self.email_re = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    def send_registry_code(self, recipient: str, numbers: str, expire: int, language: str) -> const.Code:
        try:
            subject = self.lang_register_subject[language]
            content_temp = self.lang_register_content[language]
        except KeyError:
            subject = self.lang_register_subject[self.default_language]
            content_temp = self.lang_register_content[self.default_language]

        return self._send(
            subject=subject,
            recipients=[recipient],
            html_message=content_temp.format(code=numbers, expire=expire)
        )

    def send_reset_password(self, recipient: str, numbers: str, expire: int, language: str) -> const.Code:
        try:
            subject = self.lang_reset_pwd_subject[language]
            content_temp = self.lang_reset_pwd_content[language]
        except KeyError:
            subject = self.lang_reset_pwd_subject[self.default_language]
            content_temp = self.lang_reset_pwd_content[self.default_language]

        content = content_temp.format(numbers=numbers, expire=expire)
        return self._send(
            subject=subject,
            recipients=[recipient],
            html_message=content
        )

    def email_ok(self, email_addr: str) -> bool:
        if self.email_re.fullmatch(email_addr) is None:
            return False
        return True

    def _send(self, recipients: List[str], subject: str, html_message: str) -> const.Code:
        for recipient in recipients:
            if not self.email_ok(recipient):
                return const.Code.INVALID_EMAIL
        conf = config.get_settings()
        msg = MIMEMultipart('alternative')
        msg['Subject'] = email.header.Header(subject, 'utf-8')
        msg['From'] = conf.RETHINK_EMAIL
        msg['To'] = ", ".join(recipients)
        html_body = MIMEText(html_message, 'html', 'utf-8')
        msg.attach(html_body)

        server = smtplib.SMTP('smtp.office365.com', 587)
        server.ehlo()
        server.starttls()
        server.login(conf.RETHINK_EMAIL, password=conf.RETHINK_EMAIL_PASSWORD)
        server.sendmail(conf.RETHINK_EMAIL, recipients, msg.as_string())
        server.quit()
        return const.Code.OK


email_server = EmailServer()
