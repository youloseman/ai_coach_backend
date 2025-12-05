import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_USER,
    EMAIL_PASSWORD,
    EMAIL_FROM,
    RESEND_API_KEY,
)
from email_resend import send_html_email as send_html_email_resend


def _send_via_smtp(to_email: str, subject: str, html_body: str) -> None:
    """
    Отправка HTML-письма через SMTP (например, Gmail).
    """
    if not EMAIL_USER or not EMAIL_PASSWORD:
        raise RuntimeError(
            "SMTP settings are not configured. "
            "Set EMAIL_USER/EMAIL_PASSWORD or provide RESEND_API_KEY."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    part_html = MIMEText(html_body, "html", "utf-8")
    msg.attach(part_html)

    context = ssl.create_default_context()

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls(context=context)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, [to_email], msg.as_string())


def send_html_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Отправляет письмо через Resend (если RESEND_API_KEY настроен),
    иначе падает обратно на SMTP.
    """
    if RESEND_API_KEY:
        send_html_email_resend(to_email, subject, html_body)
        return

    _send_via_smtp(to_email, subject, html_body)
