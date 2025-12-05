import smtplib, ssl

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = "podgornyiartur@gmail.com"
EMAIL_PASSWORD = "rbnm bylb lpyb tccm"

ctx = ssl.create_default_context()

try:
    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
        server.starttls(context=ctx)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
    print("SMTP test OK")
except Exception as exc:
    print("SMTP test failed:", exc)