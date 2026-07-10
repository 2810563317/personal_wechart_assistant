import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    HFWEATHER_API_KEY: str = os.getenv("HFWEATHER_API_KEY", "")
    HFWEATHER_API_HOST: str = os.getenv("HFWEATHER_API_HOST", "")
    HFWEATHER_DEFAULT_CITY: str = os.getenv("HFWEATHER_DEFAULT_CITY", "杭州")


settings = Settings()
