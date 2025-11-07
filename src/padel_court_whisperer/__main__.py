import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta
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
        current_datetime_berlin = datetime.now(berlin_tz)
        current_hour = current_datetime_berlin.hour

        # Pause during the night
        if current_hour >= 23 or current_hour < 6:
            wakeup_time = (current_datetime_berlin + timedelta(days=1)).replace(
                hour=6, minute=0, second=0, microsecond=0
            )
            if current_hour < 6:
                wakeup_time = current_datetime_berlin.replace(
                    hour=6, minute=0, second=0, microsecond=0
                )

            sleep_duration = (wakeup_time - current_datetime_berlin).total_seconds()
            sleep_duration += random.randint(0, settings.POLLING_RANDOM_DELAY_SECONDS)
            logging.info(
                f"It's nighttime. Sleeping for {sleep_duration / 3600:.2f} hours until {wakeup_time.strftime('%Y-%m-%d %H:%M:%S')}."
            )
            time.sleep(sleep_duration)
            continue

        logging.info("Checking for available slots...")

        current_date_str = current_datetime_berlin.strftime("%Y-%m-%d")

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

        previous_available_slots, last_run_date_str = load_previous_available_slots(
            settings.CACHE_FILE_PATH
        )

        # Find newly available slots and taken slots
        newly_available_slots = current_available_slots - previous_available_slots
        taken_slots = previous_available_slots - current_available_slots

        if taken_slots:
            logging.info(f"{len(taken_slots)} slots have been taken since last check.")

        # Filter out past slots
        future_newly_available_slots = set()
        for slot in newly_available_slots:
            slot_date_str, slot_time_str, _ = slot
            slot_datetime_naive = datetime.strptime(
                f"{slot_date_str} {slot_time_str}", "%Y-%m-%d %H%M"
            )
            slot_datetime = slot_datetime_naive.replace(tzinfo=berlin_tz)
            if slot_datetime > current_datetime_berlin:
                future_newly_available_slots.add(slot)

        # On the first run of a new day, filter out slots from the last day in the window
        if last_run_date_str and last_run_date_str < current_date_str:
            last_day_in_window = (current_datetime_berlin + timedelta(weeks=6)).strftime(
                "%Y-%m-%d"
            )
            slots_to_notify = {
                slot
                for slot in future_newly_available_slots
                if slot[0] != last_day_in_window
            }
            if len(slots_to_notify) < len(future_newly_available_slots):
                logging.info(
                    f"Ignoring {len(future_newly_available_slots) - len(slots_to_notify)} slots from the last day in the window on the first run of the day."
                )
            future_newly_available_slots = slots_to_notify

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
        save_available_slots(
            current_available_slots, settings.CACHE_FILE_PATH, current_date_str
        )

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
