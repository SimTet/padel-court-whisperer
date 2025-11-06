from typing import Dict

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BASE_URL: str
    FACILITY_ID: int = 77490
    SPORT: str = "padel"
    COURTS: Dict[int, str] = {
        100676: "Court 6",
        100677: "Court 7",
    }

    # Discord settings
    DISCORD_WEBHOOK_URL: str

    # Polling settings
    POLLING_INTERVAL_MINUTES: int = 10
    POLLING_RANDOM_DELAY_SECONDS: int = 30

    # Cache settings
    CACHE_FILE_PATH: str = "data/available_slots.json"
    LAST_NOTIFICATION_TIMESTAMP_FILE: str = "data/last_notification_timestamp.txt"

    class Config:
        env_file = ".env"


settings = Settings()
