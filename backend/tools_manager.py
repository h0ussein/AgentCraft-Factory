# tools_manager.py
# Tools Manager: Generate new Python tools using Gemini 2.5 Flash

import os
import re
import importlib.util
from pathlib import Path
from typing import Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Path to custom tools directory
CUSTOM_TOOLS_DIR = Path(__file__).resolve().parent / "custom_tools"
CUSTOM_TOOLS_DIR.mkdir(exist_ok=True)

# Code standards for generated tools + strict safety rules
TOOL_GENERATION_SYSTEM = """You are a Python code generator for agent tools. Your output must be safe and sandboxed.

RULES (must follow):
1. Generate ONLY a single Python function (no class, no if __name__ block).
2. The function must have a clear docstring describing what it does (this is used by the AI agent).
3. Use type hints for parameters and return type (e.g. def my_tool(query: str) -> str:).
4. NEVER hardcode API keys. For any external API that needs a key:
   - Use ONLY os.getenv('KEY_NAME') to read that key (e.g. os.getenv('OPENAI_API_KEY')).
   - If the key is missing or empty, return exactly: 'Please add your [KEY_NAME] in settings'
   - You may ONLY access the specific API key(s) required for this tool. Do NOT use os.environ, os.environ.get, or iterate over environment variables.
5. ALLOWED: requests, json, os.getenv('SOME_KEY') only. You may use: import requests, import json, and os.getenv('KEY_NAME') for the one or two keys the tool needs.
6. STRICTLY FORBIDDEN:
   - File system access: no open(), Path(), read(), write(), __file__, os.path, os.listdir, os.remove, os.mkdir, glob, or any file I/O. The only exception is that the tool must NOT access the local file system at all (generated tools run in memory only).
   - Dangerous modules: no subprocess, shutil, os.system, eval(), exec(), compile(), __import__ with user input, or similar. Do not use os for anything except os.getenv('KEY_NAME').
   - No os.environ (use only os.getenv('KEY_NAME') for the specific key needed). No pickle, shelve, or deserializing untrusted data.
7. Return a string result that the agent can show to the user. Do not print(); use return.
8. Output ONLY valid Python code for the function. No markdown code fences, no explanation before or after.
9. Function name must be a valid Python identifier (e.g. get_weather, search_web). Use snake_case."""

# Safety Review: Gemini checks generated code for malicious patterns before saving
SAFETY_REVIEW_SYSTEM = """You are a security reviewer for Python tool code. Your job is to detect forbidden or malicious patterns.

STRICTLY FORBIDDEN patterns (reply UNSAFE if any appear):
- File system: open(, Path(, read(), write(), os.path, os.listdir, os.remove, os.mkdir, glob, __file__, file I/O
- Dangerous: subprocess, shutil, os.system, eval(, exec(, compile(, __import__(, pickle, shelve
- os used for anything other than os.getenv('SOME_API_KEY') e.g. no os.environ, os.environ.get, os.path, os.listdir
- Network to non-HTTPS or internal IPs (optional: flag if present)
- Any form of code execution, shell commands, or file system writes

ALLOWED: requests.get/post, json.loads/dumps, os.getenv('NAMED_KEY') for API keys only.

Reply with exactly one line:
SAFE - if the code contains only allowed patterns and no forbidden ones.
UNSAFE: <brief reason> - if any forbidden pattern or risk is found."""


from config.gemini_keys import get_gemini_api_keys, is_retryable_gemini_error


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
    last_error = None
    for api_key in get_gemini_api_keys():
        if not api_key:
            continue
        try:
            client = genai.Client(api_key=api_key.strip())
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config,
            )
            if not response or not response.text:
                raise ValueError("Gemini did not return any code. Try again or clarify the description.")
            return response.text.strip()
        except Exception as e:
            last_error = e
            if is_retryable_gemini_error(e) and api_key != get_gemini_api_keys()[-1]:
                continue
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
    last_error = None
    for api_key in get_gemini_api_keys():
        if not api_key:
            continue
        try:
            client = genai.Client(api_key=api_key.strip())
            response = client.models.generate_content(
                model="gemini-2.5-flash",
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
                idx = raw.upper().find("UNSAFE:")
                if idx >= 0:
                    reason = raw[idx + len("UNSAFE:"):].strip() or raw
                else:
                    reason = raw
                return False, reason or "Forbidden or unsafe pattern detected."
            return False, "Safety review did not confirm SAFE."
        except Exception as e:
            last_error = e
            if is_retryable_gemini_error(e) and api_key != get_gemini_api_keys()[-1]:
                continue
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


def create_tool_file(user_description: str, tool_name: str | None = None) -> Path:
    """
    Generate a Python tool from the user's description and save it under custom_tools/.
    Includes a Safety Review step: Gemini checks the generated code for malicious patterns before saving.

    Args:
        user_description: What the tool should do (natural language).
        tool_name: Optional base name for the file (e.g. 'weather'). If None, derived from description.

    Returns:
        Path to the saved .py file.

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

    base = _sanitize_tool_name(tool_name) if tool_name else _sanitize_filename(user_description)
    # Ensure we have a unique .py file
    path = CUSTOM_TOOLS_DIR / f"{base}.py"
    counter = 0
    while path.exists():
        counter += 1
        path = CUSTOM_TOOLS_DIR / f"{base}_{counter}.py"
    path.write_text(code, encoding="utf-8")
    return path


def list_tool_files() -> list[Path]:
    """List all .py files in custom_tools/ (excluding __init__)."""
    return [p for p in CUSTOM_TOOLS_DIR.glob("*.py") if p.name != "__init__.py"]
