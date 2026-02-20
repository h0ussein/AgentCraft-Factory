# config/gemini_keys.py
# Primary + secondary + third Gemini API keys; retry with next key on 429 / quota exhausted.

import os

from dotenv import load_dotenv
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


def get_gemini_api_keys() -> list[str]:
    """
    Return API keys in order: primary (GOOGLE_API_KEY or GEMINI_API_KEY), then
    secondary (GEMINI_API_KEY_SECONDARY), then third (GEMINI_API_KEY_THIRD) if set.
    Used to fallback on 429/quota exhausted.
    """
    primary = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    secondary = (os.getenv("GEMINI_API_KEY_SECONDARY") or "").strip()
    third = (os.getenv("GEMINI_API_KEY_THIRD") or "").strip()
    keys = []
    if primary:
        keys.append(primary)
    if secondary and secondary != primary:
        keys.append(secondary)
    if third and third != primary and third != secondary:
        keys.append(third)
    return keys


def is_retryable_gemini_error(exc: BaseException) -> bool:
    """True if the error is 429 rate limit or quota/resource exhausted (try next key)."""
    # Check for status_code attribute (common in HTTP exceptions)
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    
    # Check for code attribute
    code = getattr(exc, "code", None)
    if code == 429:
        return True
    
    # Check error message for quota/rate limit indicators
    msg = (getattr(exc, "message", None) or str(exc)).lower()
    if "429" in msg or "resource_exhausted" in msg or "quota" in msg or "rate limit" in msg:
        return True
    
    # Check for HTTPError or similar exceptions
    if hasattr(exc, "response"):
        response = getattr(exc, "response", None)
        if response:
            resp_status = getattr(response, "status_code", None)
            if resp_status == 429:
                return True
    
    return False
