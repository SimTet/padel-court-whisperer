import os
import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from .api_client import (
    get_available_slots,
    load_previous_available_slots,
    save_available_slots,
)
from .config import settings
from .discord_notifier import format_discord_message, send_discord_message


def should_send_notification() -> bool:
    """Checks if a notification should be sent based on the timestamp of the last notification."""
    if not os.path.exists(settings.LAST_NOTIFICATION_TIMESTAMP_FILE):
        return False  # Don't send on first run ever

    with open(settings.LAST_NOTIFICATION_TIMESTAMP_FILE, "r") as f:
        last_timestamp_str = f.read().strip()

    if not last_timestamp_str:
        return False  # Don't send if the file is empty

    last_timestamp = datetime.fromisoformat(last_timestamp_str)
    return last_timestamp.date() == datetime.now().date()


def update_notification_timestamp():
    """Updates the timestamp of the last notification."""
    with open(settings.LAST_NOTIFICATION_TIMESTAMP_FILE, "w") as f:
        f.write(datetime.now().isoformat())


def main():
    """Main function to run the polling loop."""
    berlin_tz = ZoneInfo("Europe/Berlin")

    # --- Initialization for the first run ---
    if not os.path.exists(settings.CACHE_FILE_PATH):
        print("Cache file not found. Performing initial fetch to populate cache...")
        initial_available_slots = get_available_slots(settings.COURTS)
        save_available_slots(initial_available_slots, settings.CACHE_FILE_PATH)
        print(
            f"Initial cache populated with {len(initial_available_slots)} available slots."
        )
        # Don't send a notification on the very first run, but create the timestamp file
        update_notification_timestamp()
        time.sleep(5)

    # --- Main polling loop ---
    while True:
        print("Checking for available slots...")
        current_available_slots = get_available_slots(settings.COURTS)

        previous_available_slots = load_previous_available_slots(
            settings.CACHE_FILE_PATH
        )

        # Find newly available slots
        newly_available_slots = current_available_slots - previous_available_slots

        # Filter out past slots
        future_newly_available_slots = set()
        current_datetime_berlin = datetime.now(berlin_tz)
        for slot in newly_available_slots:
            slot_date_str, slot_time_str, _ = slot
            slot_datetime_naive = datetime.strptime(
                f"{slot_date_str} {slot_time_str}", "%Y-%m-%d %H%M"
            )
            slot_datetime = slot_datetime_naive.replace(tzinfo=berlin_tz)
            if slot_datetime > current_datetime_berlin:
                future_newly_available_slots.add(slot)

        if future_newly_available_slots:
            if should_send_notification():
                print(
                    f"Found {len(future_newly_available_slots)} newly available slots in the future!"
                )
                message_body = format_discord_message(
                    future_newly_available_slots, settings.COURTS
                )
                send_discord_message(message_body)
            else:
                print("Found new slots, but this is the first run of the day. Not sending a notification.")

            # We always update the timestamp, regardless of whether we sent a notification or not
            update_notification_timestamp()

        else:
            print("No new slots have become available in the future.")

        # Save the current state for the next run
        save_available_slots(current_available_slots, settings.CACHE_FILE_PATH)

        # Wait for the next interval
        sleep_duration = (
            settings.POLLING_INTERVAL_MINUTES * 60
        ) + random.randint(0, settings.POLLING_RANDOM_DELAY_SECONDS)
        print(f"Waiting for {sleep_duration / 60:.2f} minutes before next check...")
        time.sleep(sleep_duration)


if __name__ == "__main__":
    main()
