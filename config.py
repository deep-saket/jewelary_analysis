import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please add it to your .env file.")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
MAX_API_RETRIES = int(os.getenv("MAX_API_RETRIES", "2"))
API_RETRY_DELAY_SECONDS = float(os.getenv("API_RETRY_DELAY_SECONDS", "1.0"))
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024)))
STREAMLIT_BACKEND_URL = os.getenv("STREAMLIT_BACKEND_URL", "http://localhost:8000/analyze")
OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", "output"))
