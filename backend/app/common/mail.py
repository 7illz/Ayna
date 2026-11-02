import smtplib
import ssl
from email.message import EmailMessage

from app.common.config import get_settings


def send_reset(email: str, url: str):
    settings = get_settings()
    message = EmailMessage()
    message["From"], message["To"] = settings.smtp_from, email
    message["Subject"] = "Reset your Ayna password"
    message.set_content(
        f"Reset your password using this single-use link (expires in 30 minutes):\n{url}\n"
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_starttls:
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
