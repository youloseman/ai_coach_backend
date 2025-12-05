import resend

from config import logger, EMAIL_FROM, RESEND_API_KEY


def send_html_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Send email via Resend API
    """
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not configured")

    resend.api_key = RESEND_API_KEY

    params = {
        "from": EMAIL_FROM or "onboarding@resend.dev",
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }

    try:
        email = resend.Emails.send(params)
        logger.info("resend_email_sent", email_id=email["id"])
    except Exception as exc:
        logger.error("resend_email_failed", error=str(exc))
        raise