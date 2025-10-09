import os
import logging
from telethon import TelegramClient
from dotenv import load_dotenv

# --- CONFIGURATION & INITIALIZATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

# Load credentials from .env file
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SECRET_KEY")  # Try both names

# Initialize Telegram client only
try:
    telegram_client = TelegramClient(TELEGRAM_SESSION_NAME, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
except Exception as e:
    logging.error(f"Failed to initialize Telegram client: {e}")
    exit()

# Note: BOT_PERSONA is no longer needed as a global variable
# Age and other persona data is fetched directly from database when needed
