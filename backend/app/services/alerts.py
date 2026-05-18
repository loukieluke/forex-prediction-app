import logging

logger = logging.getLogger(__name__)


def emit_alert(message: str) -> None:
    # Lightweight placeholder for Telegram/email webhook integration.
    logger.warning("ALERT: %s", message)
