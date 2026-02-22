# services/agent_manager.py
# AgentManager: initialize any agent by ID using google-genai GenerativeModel with
# assigned tools + code_execution, thinking_level='medium', and correct Part handling.
# Supports the "Invention" loop: when the agent calls request_dynamic_tool(requirement),
# we find_or_create_tool, save to DB, and signal the caller to re-run the request.

from __future__ import annotations

import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Callable

from google import genai
from google.genai import types

try:
    from config.gemini_keys import get_gemini_api_keys, is_retryable_gemini_error
except Exception:
    get_gemini_api_keys = lambda: []
    is_retryable_gemini_error = lambda e: False

BACKEND_DIR = Path(__file__).resolve().parent.parent
CUSTOM_TOOLS_DIR = BACKEND_DIR / "custom_tools"
GENERATED_IMAGES_DIR = BACKEND_DIR / "generated_images"
GENERATED_AUDIO_DIR = BACKEND_DIR / "generated_audio"

AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".m4a", ".webm")


def _serve_image_path(image_path: str, base_url: str) -> str | None:
    """
    Copy a local image file to generated_images/ with a unique name and return the URL to serve it.
    Returns None on error. Used when a tool returns {"image_path": "/path/to/file.png"}.
    """
    try:
        path = Path(image_path)
        if not path.is_absolute():
            path = BACKEND_DIR / image_path
        path = path.resolve()
        if not path.exists() or not path.is_file():
            return None
        suffix = path.suffix.lower()
        if suffix not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            suffix = ".png"
        GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}{suffix}"
        dest = GENERATED_IMAGES_DIR / safe_name
        shutil.copy2(path, dest)
        return f"{base_url.rstrip('/')}/api/generated-images/{safe_name}"
    except Exception:
        return None


def _serve_audio_path(audio_path: str, base_url: str) -> str | None:
    """
    Copy a local audio file to generated_audio/ with a unique name and return the URL to serve it.
    Used when a tool returns {"audio_path": "/path/to/file.mp3"} (e.g. for songs).
    """
    try:
        path = Path(audio_path)
        if not path.is_absolute():
            path = BACKEND_DIR / audio_path
        path = path.resolve()
        if not path.exists() or not path.is_file():
            return None
        suffix = path.suffix.lower()
        if suffix not in AUDIO_EXTENSIONS:
            suffix = ".mp3"
        GENERATED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}{suffix}"
        dest = GENERATED_AUDIO_DIR / safe_name
        shutil.copy2(path, dest)
        return f"{base_url.rstrip('/')}/api/generated-audio/{safe_name}"
    except Exception:
        return None


_mongo_available = False
try:
    from models.agent import get_agent_by_id, get_agent_collection
    from models.tool import get_tools_by_ids, get_tool_by_id, create_tool_doc, create_dynamic_tool_doc
    from agent_factory import (
        _load_functions_from_file,
        _wrap_tool_with_key_validation,
        get_tools_for_agent,
    )
    from bson import ObjectId
    _mongo_available = True
except Exception:
    pass


def _run_saved_script_impl(script_id: str, code_body: str) -> str:
    """Run a saved script's code_body in the execution sandbox. Used by run_saved_script tool."""
    try:
        from execution_sandbox import run_restricted_source
    except Exception:
        return "Error: execution sandbox not available."
    try:
        globs = run_restricted_source(code_body, filename="<saved_script>")
        # Find the first callable that looks like a main function (e.g. run, main, execute) or any non-dunder callable
        for name, obj in globs.items():
            if name.startswith("_"):
                continue
            if callable(obj) and not isinstance(obj, type):
                try:
                    result = obj()
                    return str(result) if result is not None else "Done."
                except Exception as e:
                    return f"Script error: {e}"
        return "No callable found in script."
    except Exception as e:
        return f"Execution error: {e}"


class AgentManager:
    """
    Generic agent factory using google-genai (v2+) GenerativeModel. Loads assigned tools
    from the database and initializes a model with those tools plus built-in code_execution.
    Uses thinking_level='medium' for planning tool use.
    """

    def __init__(self, agent_id: str, user_id: str | None = None, api_key: str | None = None):
        if not _mongo_available:
            raise ValueError("MongoDB is not available. AgentManager requires MongoDB.")
        self.agent_id = agent_id
        self.user_id = user_id
        self._api_key = api_key or (get_gemini_api_keys() or [None])[0]
        if not self._api_key:
            raise ValueError("No Gemini API key. Set GOOGLE_API_KEY or GEMINI_API_KEY in .env")
        self._client = genai.Client(api_key=self._api_key.strip())
        agent_doc = get_agent_by_id(agent_id)
        if not agent_doc:
            raise ValueError(f"Agent not found: {agent_id}")
        self._agent_doc = agent_doc
        self._name = agent_doc.get("name") or "Dynamic Assistant"
        base = agent_doc.get("system_instruction") or (
            "You are a helpful AI assistant with access to tools. Use them when they can help the user."
        )
        invention_hint = (
            " If you cannot fulfill the request because you lack a suitable tool or API, "
            "call request_dynamic_tool(requirement) with a short description of what you need; "
            "a new tool will be created and your request will be retried."
        )
        self._system_instruction = base.rstrip() + invention_hint
        self._model_id = agent_doc.get("model_id") or "gemini-2.5-flash"
        self._tools_list: list[types.Tool | Callable[..., Any]] = []
        self._tool_callables: dict[str, Callable[..., Any]] = {}
        self._script_registry: dict[str, str] = {}
        self._invention_triggered: bool = False
        self._build_tools()

    def _build_tools(self) -> None:
        """Load assigned tools from DB and build tools list: callables + code_execution."""
        tool_ids = self._agent_doc.get("tools") or []
        tool_docs = get_tools_by_ids(tool_ids) if tool_ids else []
        callables_for_sdk: list[Callable[..., Any]] = []

        for t in tool_docs:
            tool_type = t.get("tool_type") or "python"
            file_path = t.get("file_path") or ""
            if tool_type == "code":
                code_body = t.get("code_body") or ""
                if not code_body:
                    continue
                script_id = str(t.get("_id", ""))
                self._script_registry[script_id] = code_body
                continue
            if file_path:
                path = Path(file_path) if Path(file_path).is_absolute() else BACKEND_DIR / file_path
                if path.exists():
                    for fn in _load_functions_from_file(path):
                        fn_wrapped = _wrap_tool_with_key_validation(fn, self.user_id)
                        callables_for_sdk.append(fn_wrapped)
                        self._tool_callables[fn.__name__] = fn_wrapped

        if self._script_registry:

            def run_saved_script(script_id: str) -> str:
                """Run a saved logic script by ID. Use when you need to execute a script that was created for you."""
                code = self._script_registry.get(script_id)
                if not code:
                    return f"Unknown script_id: {script_id}"
                return _run_saved_script_impl(script_id, code)

            run_saved_script.__name__ = "run_saved_script"
            callables_for_sdk.append(run_saved_script)
            self._tool_callables["run_saved_script"] = run_saved_script

        callables_for_sdk.append(self._request_dynamic_tool_impl)
        self._tool_callables["request_dynamic_tool"] = self._request_dynamic_tool_impl

        self._tools_list = list(callables_for_sdk)
        self._tools_list.append(types.Tool(code_execution=types.ToolCodeExecution()))

    def _request_dynamic_tool_impl(self, requirement: str) -> str:
        """
        Called when the agent requests a new tool (invention). Runs find_or_create_tool,
        saves to DB, attaches to this agent, and sets _invention_triggered so the caller can re-run.
        """
        try:
            from services.dynamic_tool_service import find_or_create_tool
        except Exception:
            from dynamic_tool_service import find_or_create_tool
        try:
            result = find_or_create_tool(requirement.strip())
        except Exception as e:
            return f"Dynamic tool creation failed: {e}"
        tool_type = result.get("type") or "script"
        name = (result.get("function_declaration") or {}).get("name") or "dynamic_tool"
        if tool_type == "api":
            fd = result.get("function_declaration") or {}
            name = fd.get("name") or "api_tool"
            description = fd.get("description") or requirement[:200]
            python_impl = (result.get("python_implementation") or "").strip()
            file_path = ""
            if python_impl:
                safe_name = re.sub(r"[^\w]", "_", name.lower())[:30]
                tool_file = CUSTOM_TOOLS_DIR / f"tool_dynamic_{safe_name}.py"
                tool_file.parent.mkdir(parents=True, exist_ok=True)
                tool_file.write_text(python_impl, encoding="utf-8")
                file_path = str(tool_file)
            tool_id = create_dynamic_tool_doc(
                name=name,
                description=description,
                tool_type="api",
                owner_agent_id=self.agent_id,
                file_path=file_path or "",
                function_declaration=fd,
            )
        else:
            code_body = result.get("python_code") or ""
            name = "script_" + (result.get("function_declaration") or {}).get("name", "logic")[:20]
            tool_id = create_dynamic_tool_doc(
                name=name,
                description=requirement[:200],
                tool_type="code",
                owner_agent_id=self.agent_id,
                code_body=code_body,
            )
        col = get_agent_collection()
        col.update_one(
            {"_id": ObjectId(self.agent_id)},
            {"$push": {"tools": tool_id}},
        )
        self._invention_triggered = True
        return f"Tool '{name}' created and attached. Your next request will have access to it."

    def _get_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=self._system_instruction,
            tools=self._tools_list,
            temperature=0.2,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MEDIUM,
            ),
        )

    def chat(
        self,
        contents: list[types.Content] | str,
        max_rounds: int = 10,
        base_url: str | None = None,
    ) -> tuple[str, bool, list[str], list[str]]:
        """
        Run chat with the agent. Handles Part types for tool calls and function responses.
        If contents is a string, it is wrapped as a single user message. Otherwise uses
        the provided list of Content (history + new message).
        Returns (final_text_response, retry_requested, image_urls, audio_urls). When retry_requested is True,
        the caller should re-run the same user message (agent will have the newly invented tool).
        Tools that create images may return a dict with "image_url"/"image_path"; tools that create
        audio/songs may return "audio_url"/"audio_path". Those are collected and served via base_url.
        """
        if isinstance(contents, str):
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=contents)],
                )
            ]
        config = self._get_config()
        current_contents = list(contents)
        collected_image_urls: list[str] = []
        collected_audio_urls: list[str] = []
        for _ in range(max_rounds):
            response = self._client.models.generate_content(
                model=self._model_id,
                contents=current_contents,
                config=config,
            )
            if not response.candidates or not response.candidates[0].content.parts:
                text = getattr(response, "text", None)
                out = (text.strip() if text else "") or "No response generated."
                return (out, self._invention_triggered, collected_image_urls, collected_audio_urls)

            parts = response.candidates[0].content.parts
            function_calls = []
            text_parts = []
            for part in parts:
                if hasattr(part, "function_call") and part.function_call:
                    function_calls.append(part)
                elif hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

            if not function_calls:
                out = "".join(text_parts) if text_parts else "No response generated."
                return (out, self._invention_triggered, collected_image_urls, collected_audio_urls)

            model_content = types.Content(role="model", parts=parts)
            current_contents.append(model_content)

            for part in function_calls:
                fc = part.function_call
                name = getattr(fc, "name", None)
                args = getattr(fc, "args", None)
                if not isinstance(args, dict):
                    args = {}
                fn = self._tool_callables.get(name) if name else None
                if fn is None:
                    result = {"error": f"Unknown tool: {name}"}
                else:
                    try:
                        out = fn(**args)
                        result = {"result": out} if not isinstance(out, dict) else out
                    except Exception as e:
                        result = {"error": str(e)}
                # Collect image and audio URLs from tool result (convention: image_url/image_path, audio_url/audio_path)
                if isinstance(result, dict):
                    if result.get("image_url") and isinstance(result["image_url"], str):
                        collected_image_urls.append(result["image_url"])
                    if result.get("image_path") and isinstance(result["image_path"], str) and base_url:
                        _url = _serve_image_path(result["image_path"], base_url)
                        if _url:
                            collected_image_urls.append(_url)
                    if result.get("audio_url") and isinstance(result["audio_url"], str):
                        collected_audio_urls.append(result["audio_url"])
                    if result.get("audio_path") and isinstance(result["audio_path"], str) and base_url:
                        _url = _serve_audio_path(result["audio_path"], base_url)
                        if _url:
                            collected_audio_urls.append(_url)
                resp_part = types.Part.from_function_response(
                    name=name or "unknown",
                    response=result,
                )
                tool_content = types.Content(role="user", parts=[resp_part])
                current_contents.append(tool_content)

            if self._invention_triggered:
                return ("A new tool was created for your request. Retrying once with the new tool.", True, collected_image_urls, collected_audio_urls)

        return ("Max tool rounds reached; please try a shorter request.", False, collected_image_urls, collected_audio_urls)


def run_agent_chat_genai(
    message: str,
    session_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    base_url: str | None = None,
) -> tuple[str, list[str], list[str]]:
    """
    Run chat using AgentManager (google-genai with tools + code_execution + thinking).
    Loads last messages from MongoDB if session_id and agent_id are set.
    Invention loop: if the agent requests a new tool (request_dynamic_tool), we create it,
    save to DB, and re-run the same message once with the new tool attached.
    Returns (response_text, image_urls, audio_urls). URLs for images/audio created by tools.
    """
    if not _mongo_available or not agent_id:
        raise ValueError("run_agent_chat_genai requires MongoDB and agent_id")
    from models.chat_history import get_last_messages, append_messages

    def build_contents() -> list[types.Content]:
        contents_list: list[types.Content] = []
        if session_id:
            last = get_last_messages(session_id, agent_id, limit=10)
            for m in last:
                role = m.get("role") or "user"
                content = (m.get("content") or "").strip()
                if not content:
                    continue
                if role == "user":
                    contents_list.append(
                        types.Content(role="user", parts=[types.Part.from_text(text=content)])
                    )
                else:
                    contents_list.append(
                        types.Content(role="model", parts=[types.Part.from_text(text=content)])
                    )
        contents_list.append(
            types.Content(role="user", parts=[types.Part.from_text(text=message)])
        )
        return contents_list

    contents_list = build_contents()
    keys = get_gemini_api_keys() or []
    last_error = None
    for api_key in keys:
        if not api_key:
            continue
        try:
            manager = AgentManager(agent_id=agent_id, user_id=user_id, api_key=api_key.strip())
            max_retries = 2
            response_text = ""
            image_urls: list[str] = []
            audio_urls: list[str] = []
            for attempt in range(max_retries):
                response_text, retry_requested, image_urls, audio_urls = manager.chat(
                    contents_list, base_url=base_url
                )
                if not retry_requested:
                    break
                if attempt + 1 < max_retries:
                    contents_list = build_contents()
            if session_id:
                try:
                    append_messages(session_id, agent_id, [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": response_text},
                    ])
                except Exception:
                    pass
            return (response_text, image_urls, audio_urls)
        except Exception as e:
            last_error = e
            if is_retryable_gemini_error(e):
                continue
            raise
    if last_error:
        raise last_error
    raise ValueError("No Gemini API key set. Add GOOGLE_API_KEY or GEMINI_API_KEY in .env")
