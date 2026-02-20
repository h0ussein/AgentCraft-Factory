# config/gemini_keys.py
# Primary + secondary Gemini API keys; retry with secondary on 429 / quota exhausted.

import os

from dotenv import load_dotenv
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


def get_gemini_api_keys() -> list[str]:
    """
    Return API keys in order: primary (GOOGLE_API_KEY or GEMINI_API_KEY), then
    secondary (GEMINI_API_KEY_SECONDARY) if set. Used to fallback on 429/quota.
    """
    primary = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    secondary = (os.getenv("GEMINI_API_KEY_SECONDARY") or "").strip()
    keys = []
    if primary:
        keys.append(primary)
    if secondary and secondary != primary:
        keys.append(secondary)
    return keys


def is_retryable_gemini_error(exc: BaseException) -> bool:
    """True if the error is 429 rate limit or quota/resource exhausted (try secondary key)."""
    msg = (getattr(exc, "message", None) or str(exc)).lower()
    code = getattr(exc, "code", None)
    if code == 429:
        return True
    if "429" in msg or "resource_exhausted" in msg or "quota" in msg or "rate limit" in msg:
        return True
    return False
