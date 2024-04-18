import smtplib

from retk import config


def task(
        recipients: list,
        subject: str,
) -> str:
    server = smtplib.SMTP('smtp.office365.com', 587)
    server.ehlo()
    server.starttls()
    settings = config.get_settings()
    try:
        server.login(settings.RETHINK_EMAIL, password=settings.RETHINK_EMAIL_PASSWORD)
    except smtplib.SMTPAuthenticationError:
        server.quit()
        return "SMTPAuthenticationError"
    try:
        server.sendmail(settings.RETHINK_EMAIL, recipients, subject)
    except smtplib.SMTPRecipientsRefused:
        server.quit()
        return "SMTPRecipientsRefused"
    server.quit()
    return "done"
