# services/dynamic_tool_service.py
# Dynamic Tool Discovery: find_or_create_tool(requirement) using Gemini 3 Flash + Google Search.
# Returns either a FunctionDeclaration (JSON Schema) for API tools or a standalone Python script for code_execution.

import json
import re
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from config.gemini_keys import (
    get_gemini_api_keys,
    get_gemini_model_for_tools,
    is_retryable_gemini_error,
)

# Gemini 3 Flash for tool discovery with Google Search (per requirement)
DYNAMIC_TOOL_MODEL = "gemini-3-flash-preview"

DYNAMIC_TOOL_SYSTEM = """You are a tool discovery assistant. Given a user requirement, you must either:
1) Find a public API or Python library that fulfills it and output a valid FunctionDeclaration (JSON Schema) for Gemini function calling, OR
2) If no suitable API/library is found, output a standalone Python logic script that can be run via code execution (no external API).

Output format (strict JSON, no markdown):
- If an API or library is found, output exactly:
{"type": "api", "function_declaration": { "name": "<snake_case_name>", "description": "<what it does>", "parameters": <OpenAPI 3.0 JSON Schema object with type, properties, required> }, "python_implementation": "<optional Python code that implements the function using requests/json/os.getenv only>"}
- If no API is found, output exactly:
{"type": "script", "python_code": "<standalone Python script: one or more functions, using only json, math, re, datetime, decimal, requests, os.getenv; no file I/O, no subprocess; return a string result>"}

Rules:
- function_declaration.name: snake_case, max 64 chars.
- parameters must be valid JSON Schema (type "object", "properties", "required").
- Python code must be safe: no open(), Path(), subprocess, eval, exec, file I/O.
- Output only the single JSON object, no explanation before or after."""


def _get_client(api_key: str | None = None) -> genai.Client:
    if api_key is None:
        keys = get_gemini_api_keys()
        if not keys:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY is not set in .env")
        api_key = keys[0]
    return genai.Client(api_key=api_key.strip())


def _extract_json(text: str) -> dict[str, Any]:
    """Extract a single JSON object from model output (strip markdown if present)."""
    text = text.strip()
    # Remove optional markdown code fence
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def find_or_create_tool(requirement: str) -> dict[str, Any]:
    """
    Use Gemini 3 Flash with Google Search to find a public API or Python library for the requirement.
    Returns either a FunctionDeclaration (with optional Python implementation) or a standalone Python script.

    Returns:
        dict with keys:
        - "type": "api" | "script"
        - "function_declaration": (if type=="api") dict suitable for types.FunctionDeclaration
        - "python_implementation": (if type=="api" and provided) str
        - "python_code": (if type=="script") str
    """
    prompt = f"""Requirement: {requirement}

Search for a public API or Python library that can fulfill this. If you find one, output a valid FunctionDeclaration (JSON Schema) and optional Python implementation. If you find none, output a standalone Python logic script. Output only the JSON object as specified."""
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(
        tools=[grounding_tool],
        temperature=0.2,
        max_output_tokens=4096,
        system_instruction=DYNAMIC_TOOL_SYSTEM,
    )
    keys = get_gemini_api_keys()
    last_error = None
    for idx, api_key in enumerate(keys):
        if not api_key:
            continue
        try:
            client = _get_client(api_key)
            response = client.models.generate_content(
                model=DYNAMIC_TOOL_MODEL,
                contents=prompt,
                config=config,
            )
            if not response or not response.text:
                raise ValueError("Gemini did not return any output for tool discovery.")
            raw = response.text.strip()
            out = _extract_json(raw)
            if out.get("type") == "api":
                fd = out.get("function_declaration") or {}
                if not isinstance(fd, dict) or not fd.get("name"):
                    raise ValueError("Invalid function_declaration in API response.")
                return {
                    "type": "api",
                    "function_declaration": fd,
                    "python_implementation": out.get("python_implementation") or "",
                }
            if out.get("type") == "script":
                code = out.get("python_code") or ""
                if not code.strip():
                    raise ValueError("Empty python_code in script response.")
                return {"type": "script", "python_code": code}
            raise ValueError(f"Unknown tool type in response: {out.get('type')}")
        except json.JSONDecodeError as e:
            last_error = ValueError(f"Tool discovery returned invalid JSON: {e}")
            break
        except Exception as e:
            last_error = e
            if is_retryable_gemini_error(e) and idx < len(keys) - 1:
                continue
            raise
    if last_error:
        raise last_error
    raise ValueError("No Gemini API key set. Add GOOGLE_API_KEY or GEMINI_API_KEY in .env")
