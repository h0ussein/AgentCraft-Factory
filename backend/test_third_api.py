"""
Test that the third Gemini API key (GEMINI_API_KEY_THIRD) is loaded and works.
Run from backend: python test_third_api.py
"""
import os
import sys

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.gemini_keys import get_gemini_api_keys

def test_third_key_loaded():
    keys = get_gemini_api_keys()
    third_env = (os.getenv("GEMINI_API_KEY_THIRD") or "").strip()
    assert third_env, "GEMINI_API_KEY_THIRD is not set in .env"
    assert len(keys) >= 3, f"Expected at least 3 keys, got {len(keys)}: {[bool(k) for k in keys]}"
    assert keys[2] == third_env, f"Third key in list should match GEMINI_API_KEY_THIRD"
    print("[OK] Third API key is loaded and is key index 2 in get_gemini_api_keys()")
    return keys[2]

def test_third_key_calls_gemini(third_key: str):
    """Call Gemini with only the third key. 429 = key valid but quota exceeded."""
    import google.genai as genai
    from google.genai import types
    from google.genai.errors import ClientError
    client = genai.Client(api_key=third_key.strip())
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with exactly: OK",
            config=types.GenerateContentConfig(temperature=0, max_output_tokens=10),
        )
    except ClientError as e:
        if getattr(e, "status_code", None) == 429 or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
            print("[OK] Third API key is valid; request returned 429 (quota exceeded). Key will be used when primary/secondary hit quota.")
            return "(429 quota - key valid)"
        raise
    # .text may be None if response has only candidates/parts
    text = getattr(response, "text", None) or ""
    if not text and getattr(response, "candidates", None):
        parts = response.candidates[0].content.parts if response.candidates else []
        text = " ".join(getattr(p, "text", "") or "" for p in parts)
    text = (text or "").strip()
    if not response:
        raise AssertionError("No response from Gemini")
    display = text or "(empty/safety)"
    print(f"[OK] Third API key successfully called Gemini (response: {display!r})")
    return text or "(empty)"

if __name__ == "__main__":
    print("Testing third Gemini API key (GEMINI_API_KEY_THIRD)...")
    third_key = test_third_key_loaded()
    test_third_key_calls_gemini(third_key)
    print("All tests passed. Third API is working.")
