from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
import smtplib
import ssl
import math
from urllib.parse import urlencode, urlsplit

from .config import Settings, settings


@dataclass(frozen=True)
class EmailDeliveryResult:
    sent: bool
    error: str | None = None


def is_smtp_configured(config: Settings = settings) -> bool:
    try:
        origin = urlsplit(config.password_reset_base_url)
    except ValueError:
        return False
    return all(
        [
            config.smtp_host,
            config.smtp_username,
            config.smtp_password,
            config.smtp_from_email or config.smtp_username,
            config.smtp_use_tls,
            math.isfinite(config.smtp_timeout_seconds) and 0 < config.smtp_timeout_seconds <= 60,
            0 < config.smtp_port <= 65535,
            origin.scheme == "https" and bool(origin.hostname) and not origin.username and not origin.password,
        ]
    )


def build_password_reset_url(email: str, token: str, config: Settings = settings) -> str:
    separator = "&" if "?" in config.password_reset_base_url else "?"
    query = urlencode({"email": email, "token": token})
    return f"{config.password_reset_base_url}{separator}{query}"


def send_password_reset_email(
    *,
    to_email: str,
    reset_token: str,
    config: Settings = settings,
) -> EmailDeliveryResult:
    if not is_smtp_configured(config):
        return EmailDeliveryResult(sent=False, error="unsafe_or_incomplete_mail_configuration")

    reset_url = build_password_reset_url(to_email, reset_token, config)
    from_email = config.smtp_from_email or config.smtp_username
    if not from_email:
        return EmailDeliveryResult(sent=False, error="SMTP from email is not configured")

    message = EmailMessage()
    message["Subject"] = "Reset your Hypertrophy App password"
    message["From"] = formataddr((config.smtp_from_name, from_email))
    message["To"] = to_email
    message.set_content(
        "\n".join(
            [
                "We received a request to reset your Hypertrophy App password.",
                "",
                "Use this secure reset link:",
                reset_url,
                "",
                "This reset token expires in 30 minutes:",
                reset_token,
                "",
                "If you did not request this, you can ignore this email.",
            ]
        )
    )

    try:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=config.smtp_timeout_seconds) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(config.smtp_username, config.smtp_password)
            smtp.send_message(message)
    except Exception:
        # SMTP exception text can contain credentials, recipients or message data.
        return EmailDeliveryResult(sent=False, error="mail_delivery_failed")

    return EmailDeliveryResult(sent=True)
