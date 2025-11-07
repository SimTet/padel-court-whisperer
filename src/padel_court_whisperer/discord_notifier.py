from datetime import datetime
from typing import Dict, Set, Tuple

from curl_cffi import requests

from .config import settings


def format_discord_message(
    future_newly_available_slots: Set[Tuple[str, str, int]],
    courts: Dict[int, str],
) -> str:
    """
    Formats the Discord message with the available slots.

    Args:
        future_newly_available_slots: A set of newly available slots in the future.
        courts: A dictionary of court IDs and their names.

    Returns:
        The formatted Discord message.
    """
    message_body = "The following court slots have become available:\n\n"
    for slot in sorted(list(future_newly_available_slots)):
        slot_date_str, slot_time_str, court_id = slot
        slot_date = datetime.strptime(slot_date_str, "%Y-%m-%d")
        formatted_date = slot_date.strftime("%d.%m.%Y")
        weekday = slot_date.strftime("%A")
        court_name = courts.get(court_id, f"Court {court_id}")
        message_body += (
            f"- {weekday}, {formatted_date}, Time: {slot_time_str}, {court_name}\n"
        )

    message_body += "\nbook here: https://www.eversports.de/widget/w/kp4ruj"
    return message_body


def send_discord_message(message: str):
    """
    Sends a message to the Discord webhook URL from the config.

    Args:
        message: The message to send.
    """
    if (
        not settings.DISCORD_WEBHOOK_URL
        or settings.DISCORD_WEBHOOK_URL == "your_discord_webhook_url_here"
    ):
        print("Discord webhook URL not configured. Skipping notification.")
        return

    data = {"content": message}
    try:
        response = requests.post(settings.DISCORD_WEBHOOK_URL, json=data)
        response.raise_for_status()
        print("Discord message sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Discord message: {e}")