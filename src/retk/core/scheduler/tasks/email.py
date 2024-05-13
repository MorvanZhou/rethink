import smtplib

from retk import config


def send(
        recipients: list,
        subject: str,
) -> str:
    server = None
    n = 3
    for _ in range(n):
        try:
            server = smtplib.SMTP('smtp.office365.com', 587)
        except smtplib.SMTPServerDisconnected:
            pass
    if server is None:
        return f"try send email task {n} times, but failed, SMTPServerDisconnected"

    server.ehlo()
    server.starttls()
    settings = config.get_settings()
    try:
        server.login(settings.RETHINK_EMAIL, password=settings.RETHINK_EMAIL_PASSWORD)
    except smtplib.SMTPAuthenticationError as e:
        server.quit()
        return f"SMTPAuthenticationError: {e}"
    try:
        server.sendmail(settings.RETHINK_EMAIL, recipients, subject)
    except smtplib.SMTPRecipientsRefused as e:
        server.quit()
        return f"SMTPRecipientsRefused: {e}"
    server.quit()
    return "done"
