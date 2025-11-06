import logging
import os
import random
import sys
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

# Configure the logger
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main():
    """Main function to run the polling loop."""
    berlin_tz = ZoneInfo("Europe/Berlin")

    # --- Main polling loop ---
    while True:
        logging.info("Checking for available slots...")

        # Check cache file age to see if we should notify
        cache_is_stale = True
        if os.path.exists(settings.CACHE_FILE_PATH):
            cache_mtime = os.path.getmtime(settings.CACHE_FILE_PATH)
            # If cache is older than twice the polling interval, consider it stale
            if (time.time() - cache_mtime) < (
                settings.POLLING_INTERVAL_MINUTES * 60 * 2
            ):
                cache_is_stale = False

        current_available_slots = get_available_slots(settings.COURTS)

        previous_available_slots = load_previous_available_slots(
            settings.CACHE_FILE_PATH
        )

        # Find newly available slots and taken slots
        newly_available_slots = current_available_slots - previous_available_slots
        taken_slots = previous_available_slots - current_available_slots

        if taken_slots:
            logging.info(f"{len(taken_slots)} slots have been taken since last check.")

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
            if not cache_is_stale:
                logging.info(
                    f"Found {len(future_newly_available_slots)} newly available slots in the future!"
                )
                message_body = format_discord_message(
                    future_newly_available_slots, settings.COURTS
                )
                send_discord_message(message_body)
            else:
                logging.info(
                    f"Found {len(future_newly_available_slots)} new slots, but cache is stale. Not sending a notification to avoid spam."
                )

        else:
            logging.info("No new slots have become available in the future.")

        # Save the current state for the next run
        save_available_slots(current_available_slots, settings.CACHE_FILE_PATH)

        # Wait for the next interval
        sleep_duration = (
            settings.POLLING_INTERVAL_MINUTES * 60
        ) + random.randint(0, settings.POLLING_RANDOM_DELAY_SECONDS)
        logging.info(
            f"Waiting for {sleep_duration / 60:.2f} minutes before next check..."
        )
        time.sleep(sleep_duration)


if __name__ == "__main__":
    main()
