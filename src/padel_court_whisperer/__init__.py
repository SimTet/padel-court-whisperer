"""Padel Court Whisperer."""

__all__ = [
    "__version__",
    "get_available_slots",
    "format_discord_message",
    "send_discord_message",
    "send_heartbeat_message",
]


from .api_client import get_available_slots
from .discord_notifier import (
    format_discord_message,
    send_discord_message,
    send_heartbeat_message,
)
from .version import __version__
