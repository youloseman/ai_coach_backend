import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM


def send_html_email(to_email: str, subject: str, html_body: str):
    """
    Простая отправка HTML-письма через SMTP (Gmail).
    """
    if not EMAIL_USER or not EMAIL_PASSWORD:
        raise RuntimeError("Email settings are not configured. Check EMAIL_USER and EMAIL_PASSWORD in .env")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    # HTML-версия
    part_html = MIMEText(html_body, "html", "utf-8")
    msg.attach(part_html)

    context = ssl.create_default_context()

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls(context=context)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, [to_email], msg.as_string())
