import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "Salon Buchungsassistent"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./salon_booking.db")

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-use-random-32-chars")

settings = Settings()
