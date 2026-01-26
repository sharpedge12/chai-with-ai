import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration from environment variables"""
    
    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    LOGS_DIR = PROJECT_ROOT / "logs"
    
    # Ensure directories exist
    DATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "digest.db"))
    
    # LLM Configuration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4_K_M")
    
    # Persona Settings
    PERSONA_GENAI_NEWS_ENABLED = os.getenv("PERSONA_GENAI_NEWS_ENABLED", "true").lower() == "true"
    PERSONA_PRODUCT_IDEAS_ENABLED = os.getenv("PERSONA_PRODUCT_IDEAS_ENABLED", "true").lower() == "true"
    
    # Content Filtering
    GENAI_NEWS_MIN_RELEVANCE = float(os.getenv("GENAI_NEWS_MIN_RELEVANCE", "0.6"))
    PRODUCT_IDEAS_MIN_REUSABILITY = float(os.getenv("PRODUCT_IDEAS_MIN_REUSABILITY", "0.5"))
    CONTENT_HOURS_LOOKBACK = int(os.getenv("CONTENT_HOURS_LOOKBACK", "24"))
    
    # Reddit API
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "DigestBot/1.0")
    
    # Email
    EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST")
    EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    EMAIL_FROM = os.getenv("EMAIL_FROM")
    EMAIL_TO = os.getenv("EMAIL_TO")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
    # Telegram
    TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "digest.log"))

# Global config instance
config = Config()