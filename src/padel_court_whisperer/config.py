from typing import Dict

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BASE_URL: str
    FACILITY_ID: int
    SPORT: str = "padel"
    COURTS: Dict[int, str] 

    # Discord settings
    DISCORD_WEBHOOK_URL: str

    # Polling settings
    POLLING_INTERVAL_MINUTES: int
    POLLING_RANDOM_DELAY_SECONDS: int

    # Cache settings
    CACHE_FILE_PATH: str = "data/available_slots.json"

    class Config:
        env_file = ".env"


settings = Settings()
