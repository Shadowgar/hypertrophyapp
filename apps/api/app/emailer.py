from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
import smtplib
from urllib.parse import urlencode

from .config import Settings, settings


@dataclass(frozen=True)
class EmailDeliveryResult:
    sent: bool
    error: str | None = None


def is_smtp_configured(config: Settings = settings) -> bool:
    return all(
        [
            config.smtp_host,
            config.smtp_username,
            config.smtp_password,
            config.smtp_from_email or config.smtp_username,
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
        return EmailDeliveryResult(sent=False, error="SMTP is not configured")

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
            if config.smtp_use_tls:
                smtp.starttls()
            smtp.login(config.smtp_username, config.smtp_password)
            smtp.send_message(message)
    except Exception as exc:  # pragma: no cover - exact SMTP errors depend on provider/network.
        return EmailDeliveryResult(sent=False, error=str(exc))

    return EmailDeliveryResult(sent=True)
