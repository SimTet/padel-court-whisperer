import json
from datetime import datetime, timedelta
from typing import Any, Dict, Set, Tuple
from zoneinfo import ZoneInfo

from curl_cffi import requests

from .config import settings


def get_slots(
    facility_id: int,
    sport: str,
    start_date: str,
    courts: Dict[int, str],
) -> Dict[str, Any]:
    """
    Fetches available slots from the Eversports API.

    Args:
        facility_id: The ID of the facility.
        sport: The sport to query (e.g., "padel").
        start_date: The start date in "YYYY-MM-DD" format.
        courts: A list of court IDs.

    Returns:
        A dictionary containing the JSON response from the API.
    """
    params = {
        "facilityId": facility_id,
        "sport": sport,
        "startDate": start_date,
    }
    # Add courts as an array of parameters
    for court_id in courts:
        params["courts[]"] = params.get("courts[]", []) + [court_id]

    try:
        response = requests.get(
            settings.BASE_URL,
            params=params,
            impersonate="chrome",
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return {}


def get_unavailable_slots_from_response(api_response: Dict[str, Any]) -> Set[Tuple[str, str, int]]:
    """Extracts a set of unavailable slots from the API response."""
    unavailable_slots = set()
    if api_response and "slots" in api_response:
        for slot in api_response["slots"]:
            unavailable_slots.add((slot["date"], slot["start"], slot["court"]))
    return unavailable_slots


def get_all_possible_slots(
    target_date: str,
    courts: Dict[int, str],
    start_time_hour: int = 8,
    end_time_hour: int = 21,
) -> Set[Tuple[str, str, int]]:
    """
    Generates all possible slots for a given date, courts, and time range.
    """
    all_possible_slots = set()
    for court_id in courts:
        for hour in range(start_time_hour, end_time_hour + 1):
            time_str = f"{hour:02d}00"
            all_possible_slots.add((target_date, time_str, court_id))
    return all_possible_slots


def get_available_slots(courts: Dict[int, str]) -> Set[Tuple[str, str, int]]:
    """
    Fetches available slots for a given number of days.

    Args:
        courts: A dictionary of court IDs and their names.

    Returns:
        A set of available slots.
    """
    berlin_tz = ZoneInfo("Europe/Berlin")
    current_datetime_berlin = datetime.now(berlin_tz)
    all_unavailable_slots = set()
    all_possible_slots = set()

    for i in range(6):  # Check for the next 6 weeks
        check_date = current_datetime_berlin + timedelta(weeks=i)
        start_date = check_date.strftime("%Y-%m-%d")
        slots_data = get_slots(
            settings.FACILITY_ID,
            settings.SPORT,
            start_date,
            courts,
        )
        if slots_data:
            all_unavailable_slots.update(get_unavailable_slots_from_response(slots_data))

        # Since the API returns slots for one week, we need to generate all possible slots for 7 days
        for j in range(7):
            day_to_check = check_date + timedelta(days=j)
            date_str = day_to_check.strftime("%Y-%m-%d")
            all_possible_slots.update(get_all_possible_slots(date_str, courts))

    return all_possible_slots - all_unavailable_slots


def load_previous_available_slots(cache_file: str) -> Set[Tuple[str, str, int]]:
    """Loads the set of available slots from a cache file and removes old entries."""
    try:
        with open(cache_file, "r") as f:
            slots = {tuple(slot) for slot in json.load(f)}
            today = datetime.now().date()
            return {
                slot
                for slot in slots
                if datetime.strptime(slot[0], "%Y-%m-%d").date() >= today
            }
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_available_slots(available_slots: Set[Tuple[str, str, int]], cache_file: str):
    """Saves the set of available slots to a cache file."""
    with open(cache_file, "w") as f:
        json.dump(list(available_slots), f)
