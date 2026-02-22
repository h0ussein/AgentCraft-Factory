# config/gemini_keys.py
# Primary + secondary + third Gemini API keys; retry with next key on 429 / quota exhausted.
# Supported models: Gemini 2.5 Flash, 2.5 Pro, 3 Flash (all API keys can use any of these).

import os

from dotenv import load_dotenv
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

# Model IDs supported by the Gemini API (usable with any of the API keys)
GEMINI_MODEL_2_5_FLASH = "gemini-2.5-flash"
GEMINI_MODEL_2_5_PRO = "gemini-2.5-pro"
GEMINI_MODEL_3_FLASH = "gemini-3-flash-preview"

ALLOWED_GEMINI_MODELS = (GEMINI_MODEL_2_5_FLASH, GEMINI_MODEL_2_5_PRO, GEMINI_MODEL_3_FLASH)


def get_gemini_model_for_tools() -> str:
    """
    Model used for tool generation, safety review, and public key detection.
    Set GEMINI_MODEL_TOOLS in .env to gemini-2.5-pro or gemini-3-flash-preview to override.
    """
    env = (os.getenv("GEMINI_MODEL_TOOLS") or "").strip().lower()
    if env in ALLOWED_GEMINI_MODELS:
        return env
    return GEMINI_MODEL_2_5_FLASH

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
    """True if the error is 429 rate limit or quota/resource exhausted (try next key, including third)."""
    def check(e: BaseException | None) -> bool:
        if e is None:
            return False
        status_code = getattr(e, "status_code", None)
        if status_code == 429:
            return True
        code = getattr(e, "code", None)
        if code == 429:
            return True
        msg = (getattr(e, "message", None) or str(e)).lower()
        if "429" in msg or "resource_exhausted" in msg or "quota" in msg or "rate limit" in msg:
            return True
        if hasattr(e, "response") and getattr(e.response, "status_code", None) == 429:
            return True
        return False

    if check(exc):
        return True
    if getattr(exc, "__cause__", None):
        if check(exc.__cause__):
            return True
    if getattr(exc, "__context__", None):
        if check(exc.__context__):
            return True
    return False
