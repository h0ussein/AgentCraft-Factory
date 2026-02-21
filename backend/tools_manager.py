# tools_manager.py
# Tools Manager: Generate new Python tools using Gemini 2.5 Flash

import os
import re
import importlib.util
from pathlib import Path
from typing import Tuple, Dict, List
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Path to custom tools directory
CUSTOM_TOOLS_DIR = Path(__file__).resolve().parent / "custom_tools"
CUSTOM_TOOLS_DIR.mkdir(exist_ok=True)

# Code standards for generated tools + strict safety rules (no privacy/attack capability)
TOOL_GENERATION_SYSTEM = """You are a Python code generator for agent tools. Your output must be safe and sandboxed. Tools must NEVER access the file system, run shell commands, or do anything that could compromise privacy or attack a system.

RULES (must follow):
1. Generate ONLY a single Python function (no class, no if __name__ block).
2. The function must have a clear docstring describing what it does (this is used by the AI agent).
3. Use type hints for parameters and return type (e.g. def my_tool(query: str) -> str:).
4. For tools that need NO external API (e.g. math, string processing, calculations): use only the ALLOWED modules below. No os.getenv needed.
5. For tools that call an external API: NEVER hardcode API keys. Use ONLY os.getenv('KEY_NAME') to read that key. If the key is missing, return exactly: 'Please add your [KEY_NAME] in settings'. Do NOT use os.environ or os.environ.get.
6. ALLOWED modules: math, json, re, requests (for HTTP only), datetime, decimal. For API keys: os.getenv('KEY_NAME') only.
7. STRICTLY FORBIDDEN (never generate these):
   - File system: open(), Path(), read(), write(), __file__, os.path, os.listdir, os.remove, os.mkdir, glob, any file I/O.
   - Code execution or shell: subprocess, shutil, os.system, eval(), exec(), compile(), __import__ with user input.
   - Security risks: pickle, shelve, deserializing untrusted data, accessing internal IPs or non-HTTPS endpoints for sensitive data.
   - Anything that could steal data, attack a server, or access resources outside the tool's stated purpose.
8. Return a string result that the agent can show to the user. Do not print(); use return.
9. Output ONLY valid Python code for the function. No markdown code fences, no explanation before or after.
10. Function name must be a valid Python identifier (e.g. get_weather, do_math). Use snake_case."""

# Safety Review: block anything that could harm privacy or attack systems
SAFETY_REVIEW_SYSTEM = """You are a security reviewer for Python tool code. Reject anything that could compromise privacy, attack a system, or access resources outside the tool's purpose.

STRICTLY FORBIDDEN (reply UNSAFE if any appear):
- File system: open(, Path(, read(), write(), os.path, os.listdir, os.remove, os.mkdir, glob, __file__, any file I/O
- Code execution/shell: subprocess, shutil, os.system, eval(, exec(, compile(, __import__( with user input
- Dangerous: pickle, shelve, deserialize untrusted data
- os used for anything other than os.getenv('SOME_API_KEY') e.g. no os.environ, os.environ.get, os.path, os.listdir
- Network to internal IPs, non-HTTPS for sensitive data, or any pattern that could be used to probe/attack

ALLOWED: math, json, re, datetime, decimal, requests.get/post to public HTTPS APIs, os.getenv('NAMED_KEY') for API keys only.

Reply with exactly one line:
SAFE - if the code contains only allowed patterns and no forbidden ones.
UNSAFE: <brief reason> - if any forbidden pattern or risk is found."""


from config.gemini_keys import get_gemini_api_keys, get_gemini_model_for_tools, is_retryable_gemini_error


def _get_genai_client(api_key: str | None = None):
    """Create GenAI client. If api_key is None, uses first key from get_gemini_api_keys()."""
    if api_key is None:
        keys = get_gemini_api_keys()
        if not keys:
            raise ValueError(
                "Please add GOOGLE_API_KEY or GEMINI_API_KEY in .env"
            )
        api_key = keys[0]
    return genai.Client(api_key=api_key.strip())


def _sanitize_filename(name: str) -> str:
    """Convert a description into a safe Python module filename."""
    # Take first few words, alphanumeric + underscore only
    safe = re.sub(r"[^\w\s]", "", name)
    safe = re.sub(r"\s+", "_", safe.strip().lower())[:40]
    return f"tool_{safe}" if safe else "tool_custom"


def _sanitize_tool_name(name: str) -> str:
    """Sanitize user-provided tool name (no 'tool_' prefix)."""
    safe = re.sub(r"[^\w]", "_", name.strip().lower())[:40]
    return safe or "tool"


def generate_tool_code(user_description: str) -> str:
    """
    Ask Gemini 2.5 Flash to write a Python function. Uses secondary API key on 429/quota.
    """
    prompt = f"""Create a Python function for this tool:

Description: {user_description}

Remember: Use only os.getenv('KEY_NAME') for API keys; no file system, no subprocess/shutil, no os.environ. If key missing, return 'Please add your [KEY_NAME] in settings'.
Output only the function code, no markdown."""
    config = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=2048,
        system_instruction=TOOL_GENERATION_SYSTEM,
    )
    keys = get_gemini_api_keys()
    last_error = None
    for idx, api_key in enumerate(keys):
        if not api_key:
            continue
        try:
            client = genai.Client(api_key=api_key.strip())
            response = client.models.generate_content(
                model=get_gemini_model_for_tools(),
                contents=prompt,
                config=config,
            )
            if not response or not response.text:
                raise ValueError("Gemini did not return any code. Try again or clarify the description.")
            return response.text.strip()
        except Exception as e:
            last_error = e
            # If it's a retryable error and we have more keys to try, continue to next key
            if is_retryable_gemini_error(e):
                if idx < len(keys) - 1:
                    # Try next key
                    continue
                else:
                    # This was the last key, raise the error
                    raise
            # Non-retryable error, raise immediately
            raise
    if last_error:
        raise last_error
    raise ValueError("No Gemini API key set. Add GOOGLE_API_KEY or GEMINI_API_KEY in .env")


def _safety_review_generated_code(code: str) -> Tuple[bool, str]:
    """
    Safety Review step: Gemini checks the generated code. Uses secondary key on 429/quota.
    """
    prompt = f"""Review this Python tool code for forbidden patterns. Reply with SAFE or UNSAFE and reason.

Code:
```
{code}
```"""
    config = types.GenerateContentConfig(
        temperature=0,
        max_output_tokens=256,
        system_instruction=SAFETY_REVIEW_SYSTEM,
    )
    keys = get_gemini_api_keys()
    last_error = None
    for idx, api_key in enumerate(keys):
        if not api_key:
            continue
        try:
            client = genai.Client(api_key=api_key.strip())
            response = client.models.generate_content(
                model=get_gemini_model_for_tools(),
                contents=prompt,
                config=config,
            )
            if not response or not response.text:
                return False, "Safety review could not be completed (no response)."
            text = response.text.strip().upper()
            if text.startswith("SAFE"):
                return True, "SAFE"
            if "UNSAFE" in text:
                raw = response.text.strip()
                unsafe_idx = raw.upper().find("UNSAFE:")
                if unsafe_idx >= 0:
                    reason = raw[unsafe_idx + len("UNSAFE:"):].strip() or raw
                else:
                    reason = raw
                return False, reason or "Forbidden or unsafe pattern detected."
            return False, "Safety review did not confirm SAFE."
        except Exception as e:
            last_error = e
            # If it's a retryable error and we have more keys to try, continue to next key
            if is_retryable_gemini_error(e):
                if idx < len(keys) - 1:
                    # Try next key
                    continue
                else:
                    # This was the last key, raise the error
                    raise
            # Non-retryable error, raise immediately
            raise
    if last_error:
        raise last_error
    return False, "Safety review failed (no API key)."


def _strip_markdown_code_block(text: str) -> str:
    """Remove ```python ... ``` if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


def extract_api_key_requirements(code: str) -> List[str]:
    """
    Extract API key names from generated tool code by finding os.getenv('KEY_NAME') patterns.
    
    Returns:
        List of API key names (e.g., ['OPENWEATHER_API_KEY', 'OPENAI_API_KEY'])
    """
    # Pattern: os.getenv('KEY_NAME') or os.getenv("KEY_NAME")
    pattern = r'os\.getenv\(["\']([^"\']+)["\']\)'
    matches = re.findall(pattern, code)
    # Remove duplicates and return sorted list
    return sorted(list(set(matches)))


def detect_public_api_keys(user_description: str, required_keys: List[str]) -> Dict[str, str]:
    """
    Use Gemini to detect if any of the required API keys have public/free tier options.
    Returns dict mapping KEY_NAME -> public_key_value if found, empty dict otherwise.
    
    Args:
        user_description: Original tool description
        required_keys: List of API key names detected from code
        
    Returns:
        Dict with KEY_NAME -> public_key_value for keys that have public options
    """
    if not required_keys:
        return {}
    
    prompt = f"""You must search for public or free-tier API keys that match the tool's needs.

Tool description: {user_description}

Required API keys (env names the tool uses): {', '.join(required_keys)}

Task: For each required key, if that API has a known public key, free tier key, or demo key that works for testing, provide it.
- OpenWeatherMap: has a free tier; use a well-known demo/test key if you know one, or a placeholder like "demo" only if the API accepts it.
- CoinGecko: often allows requests without a key or with a public base URL; if the tool needs COINGECKO_API_KEY, provide a known public/demo value if one exists.
- Other APIs: search your knowledge for any public, free-tier, or demo key that matches the KEY_NAME.

Output format: one line per key you can fill, exactly "KEY_NAME: value" (use the exact KEY_NAME from the list above). No other text.
If you find a real public/demo key value, use it. If you truly have no public key for any of them, reply with exactly: NONE."""
    
    config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=512,
    )
    keys = get_gemini_api_keys()
    last_error = None
    for idx, api_key in enumerate(keys):
        if not api_key:
            continue
        try:
            client = genai.Client(api_key=api_key.strip())
            response = client.models.generate_content(
                model=get_gemini_model_for_tools(),
                contents=prompt,
                config=config,
            )
            if not response or not response.text:
                return {}
            text = response.text.strip()
            # Only treat as "no keys" if response is just NONE (or similar)
            if text.upper().strip() in ("NONE", "N/A", "NONE."):
                return {}
            if "NONE" in text.upper() and len(text.split()) <= 2:
                return {}

            # Parse KEY_NAME: value pairs
            detected_keys = {}
            for line in text.split('\n'):
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key_name = parts[0].strip()
                        key_value = parts[1].strip()
                        if key_value and key_name in required_keys:
                            detected_keys[key_name] = key_value
            return detected_keys
        except Exception as e:
            last_error = e
            if is_retryable_gemini_error(e):
                if idx < len(keys) - 1:
                    continue
                else:
                    break
            # Non-retryable error, return empty
            break
    return {}


def create_tool_file(user_description: str, tool_name: str | None = None) -> Tuple[Path, Dict[str, str]]:
    """
    Generate a Python tool from the user's description and save it under custom_tools/.
    Includes a Safety Review step: Gemini checks the generated code for malicious patterns before saving.
    Also extracts API key requirements and detects public API keys if available.

    Args:
        user_description: What the tool should do (natural language).
        tool_name: Optional base name for the file (e.g. 'weather'). If None, derived from description.

    Returns:
        Tuple of (Path to saved .py file, Dict of detected public API keys {KEY_NAME: value})

    Raises:
        ValueError: If generation fails, safety review fails, or API key is missing.
    """
    code = generate_tool_code(user_description)
    code = _strip_markdown_code_block(code)

    # Safety Review step: Gemini checks its own generated code before saving
    is_safe, safety_message = _safety_review_generated_code(code)
    if not is_safe:
        raise ValueError(
            f"Safety review failed. The generated code was rejected: {safety_message}. "
            "Safety review failed: generated code contains forbidden patterns."
        )

    # Extract API key requirements from code
    required_keys = extract_api_key_requirements(code)
    
    # Try to detect public API keys if any are required
    public_keys = {}
    if required_keys:
        public_keys = detect_public_api_keys(user_description, required_keys)

    base = _sanitize_tool_name(tool_name) if tool_name else _sanitize_filename(user_description)
    # Ensure we have a unique .py file
    path = CUSTOM_TOOLS_DIR / f"{base}.py"
    counter = 0
    while path.exists():
        counter += 1
        path = CUSTOM_TOOLS_DIR / f"{base}_{counter}.py"
    path.write_text(code, encoding="utf-8")
    return path, public_keys


def generate_tool_code_and_keys(user_description: str, tool_name: str | None = None) -> Tuple[str, str, List[str], Dict[str, str]]:
    """
    Generate tool code, run safety review, extract required API keys, and detect public keys.
    Does NOT write any file. Caller must resolve keys (admin + public) and then call write_tool_file if all resolved.

    Returns:
        (code, base_name, required_keys, public_keys)
    """
    code = generate_tool_code(user_description)
    code = _strip_markdown_code_block(code)
    is_safe, safety_message = _safety_review_generated_code(code)
    if not is_safe:
        raise ValueError(
            f"Safety review failed. The generated code was rejected: {safety_message}. "
            "Safety review failed: generated code contains forbidden patterns."
        )
    required_keys = extract_api_key_requirements(code)
    public_keys = {}
    if required_keys:
        public_keys = detect_public_api_keys(user_description, required_keys)
    base = _sanitize_tool_name(tool_name) if tool_name else _sanitize_filename(user_description)
    return code, base, required_keys, public_keys


def write_tool_file(code: str, base_name: str) -> Path:
    """Write code to a new file under custom_tools/ with unique name. Returns path."""
    path = CUSTOM_TOOLS_DIR / f"{base_name}.py"
    counter = 0
    while path.exists():
        counter += 1
        path = CUSTOM_TOOLS_DIR / f"{base_name}_{counter}.py"
    path.write_text(code, encoding="utf-8")
    return path


def list_tool_files() -> list[Path]:
    """List all .py files in custom_tools/ (excluding __init__)."""
    return [p for p in CUSTOM_TOOLS_DIR.glob("*.py") if p.name != "__init__.py"]
