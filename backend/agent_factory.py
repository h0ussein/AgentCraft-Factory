# agent_factory.py
# Agent factory: build_my_agent(agent_id) loads agent tools from MongoDB only
# Memory: sync chat history with MongoDB (ChatHistory)
# Validation: verify API keys in User document before executing tools

import os
import re
import sys
import inspect
import importlib.util
from pathlib import Path
from typing import Callable
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini

load_dotenv()

try:
    from config.gemini_keys import get_gemini_api_keys, is_retryable_gemini_error
except Exception:
    get_gemini_api_keys = lambda: []
    is_retryable_gemini_error = lambda e: False

CUSTOM_TOOLS_DIR = Path(__file__).resolve().parent / "custom_tools"
BACKEND_DIR = Path(__file__).resolve().parent

try:
    from models.agent import get_agent_by_id, ensure_default_agent
    from models.tool import get_tools_by_ids
    from models.chat_history import get_last_messages, append_messages
    from models.user import get_user_api_keys
    _mongo_available = True
except Exception:
    _mongo_available = False


def _is_tool_function(obj: Callable) -> bool:
    if not callable(obj):
        return False
    if obj.__name__.startswith("_"):
        return False
    return callable(obj) and hasattr(obj, "__doc__")


def _get_required_env_keys_from_func(fn: Callable) -> list[str]:
    """
    Parse function source for os.getenv('KEY') or os.getenv("KEY") and return key names.
    """
    keys = []
    try:
        source = inspect.getsource(fn)
        # Match os.getenv('KEY'), os.getenv("KEY"), os.environ.get('KEY'), etc.
        for m in re.finditer(r"(?:os\.getenv|os\.environ\.get)\s*\(\s*['\"]([^'\"]+)['\"]", source):
            keys.append(m.group(1))
    except Exception:
        pass
    return list(dict.fromkeys(keys))


def _wrap_tool_with_key_validation(fn: Callable, user_id: str | None) -> Callable:
    """
    Wrap a tool so that before execution we check required API keys exist in User document or env.
    If user_id is not set, run the tool as-is.
    """
    if not user_id or not _mongo_available:
        return fn
    required = _get_required_env_keys_from_func(fn)
    if not required:
        return fn

    def wrapped(*args, **kwargs):
        user_keys = get_user_api_keys(user_id)
        missing = []
        for k in required:
            if not (os.getenv(k) or user_keys.get(k)):
                missing.append(k)
        if missing:
            return "Please add your [" + ", ".join(missing) + "] in settings."
        return fn(*args, **kwargs)

    wrapped.__name__ = fn.__name__
    wrapped.__doc__ = fn.__doc__
    return wrapped


def _load_functions_from_file(file_path: Path) -> list[Callable]:
    """
    Load a .py file and return all top-level callable functions (tools).
    Uses the execution sandbox: code runs in a restricted environment (RestrictedPython if available).
    Only files under custom_tools/ are allowed; the Agent can only execute functions defined there.
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    if not path.exists():
        return []
    try:
        path = path.resolve()
        path.relative_to(CUSTOM_TOOLS_DIR.resolve())
    except (ValueError, Exception):
        return []

    try:
        from execution_sandbox import load_tool_functions_from_source
        source_code = path.read_text(encoding="utf-8")
        funcs = load_tool_functions_from_source(
            source_code,
            filename=path.name,
            custom_tools_dir=CUSTOM_TOOLS_DIR,
            file_path_resolved=path,
        )
        return [f for f in funcs if _is_tool_function(f)]
    except Exception:
        pass

    # Fallback: load without sandbox only if sandbox failed (e.g. RestrictedPython not installed)
    # Still enforce: only from custom_tools/
    name = path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return []
    module = importlib.util.module_from_spec(spec)
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    try:
        spec.loader.exec_module(module)
    except Exception:
        return []
    funcs = []
    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue
        obj = getattr(module, attr_name)
        if _is_tool_function(obj):
            funcs.append(obj)
    return funcs


def get_all_custom_tools() -> list[Callable]:
    """Scan custom_tools/ and return all loaded tool functions (fallback when no agent_id)."""
    tools: list[Callable] = []
    if not CUSTOM_TOOLS_DIR.exists():
        return tools
    for path in sorted(CUSTOM_TOOLS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tools.extend(_load_functions_from_file(path))
    return tools


def get_tools_for_agent(agent_id: str, user_id: str | None = None) -> list[Callable]:
    """
    Load only the tools linked to this agent in the database (by tool IDs).
    Imports only those .py files from custom_tools/ (via file_path in Tool docs).
    Optionally wraps each tool with API key validation against User document.
    """
    if not _mongo_available:
        return []
    agent_doc = get_agent_by_id(agent_id)
    if not agent_doc or not agent_doc.get("tools"):
        return []
    tool_docs = get_tools_by_ids(agent_doc["tools"])
    funcs: list[Callable] = []
    for t in tool_docs:
        fp = t.get("file_path")
        if not fp:
            continue
        loaded = _load_functions_from_file(Path(fp))
        for fn in loaded:
            funcs.append(_wrap_tool_with_key_validation(fn, user_id))
    return funcs


def build_my_agent(agent_id: str, user_id: str | None = None, instructions: str | None = None) -> Agent:
    """
    Build an agent by agent_id: fetch agent from MongoDB and load only its linked tools
    from custom_tools/ (via Tool documents' file_path). No fallback to all custom_tools.
    If user_id is set, inject user's API keys into env and validate tools against User document.
    """
    if not _mongo_available:
        raise ValueError("MongoDB is not available. agent_id requires MongoDB.")
    agent_doc = get_agent_by_id(agent_id)
    if not agent_doc:
        raise ValueError(f"Agent not found: {agent_id}")

    name = agent_doc.get("name") or "Dynamic Assistant"
    system_instruction = agent_doc.get("system_instruction") or (
        "You are a helpful AI assistant with access to tools. "
        "Always check your available tools and use them when they can help the user."
    )
    model_id = agent_doc.get("model_id") or "gemini-2.5-flash"
    tools_list = get_tools_for_agent(agent_id, user_id=user_id)

    if instructions:
        system_instruction = system_instruction + "\n" + instructions

    return Agent(
        name=name,
        model=Gemini(id=model_id),
        tools=tools_list if tools_list else None,
        instructions=system_instruction,
        markdown=True,
    )


def create_dynamic_agent(
    agent_id: str | None = None,
    user_id: str | None = None,
    instructions: str | None = None,
    add_custom_tools: bool = True,
) -> Agent:
    """
    Create an Agno Agent. If agent_id is set, uses build_my_agent (DB-only tools).
    Otherwise uses default config and optionally all custom_tools/.
    """
    if _mongo_available and agent_id:
        return build_my_agent(agent_id, user_id=user_id, instructions=instructions)

    name = "Dynamic Assistant"
    system_instruction = (
        "You are a helpful AI assistant with access to tools. "
        "Always check your available tools and use them when they can help the user."
    )
    model_id = "gemini-2.5-flash"
    tools_list: list[Callable] = get_all_custom_tools() if add_custom_tools else []
    if user_id and _mongo_available:
        tools_list = [_wrap_tool_with_key_validation(f, user_id) for f in tools_list]

    if instructions:
        system_instruction = system_instruction + "\n" + instructions

    return Agent(
        name=name,
        model=Gemini(id=model_id),
        tools=tools_list if tools_list else None,
        instructions=system_instruction,
        markdown=True,
    )


def run_agent_chat(
    message: str,
    session_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """
    Run the agent. Memory: sync with MongoDB ChatHistory (load last 10 messages as context,
    append user + assistant message after run). If user_id is set, inject User's api_keys
    into env and validate tool API keys against User document before executing tools.
    """
    if _mongo_available:
        try:
            ensure_default_agent()
        except Exception:
            pass

    # Inject User's API keys into environment for this run (for tools that use os.getenv)
    injected_env = {}
    if user_id and _mongo_available:
        user_keys = get_user_api_keys(user_id)
        for k, v in user_keys.items():
            if v and not os.getenv(k):
                injected_env[k] = os.environ.get(k)
                os.environ[k] = str(v)

    keys = get_gemini_api_keys()
    saved_gemini = {
        "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY"),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
    }
    last_error = None
    try:
        for idx, api_key in enumerate(keys):
            if not api_key:
                continue
            os.environ["GOOGLE_API_KEY"] = api_key
            os.environ["GEMINI_API_KEY"] = api_key
            try:
                agent = create_dynamic_agent(agent_id=agent_id, user_id=user_id)
                effective_agent_id = agent_id
                if _mongo_available and not effective_agent_id:
                    from config.db import get_db_if_connected
                    db = get_db_if_connected()
                    if db is not None:
                        first = db.agents.find_one()
                        if first:
                            effective_agent_id = str(first["_id"])

                history_input = None
                if _mongo_available and session_id and effective_agent_id:
                    last_10 = get_last_messages(session_id, effective_agent_id, limit=10)
                    if last_10:
                        history_input = []
                        for m in last_10:
                            history_input.append({
                                "role": m.get("role") or "user",
                                "content": m.get("content") or "",
                            })
                        history_input.append({"role": "user", "content": message})
                if history_input is None:
                    history_input = message

                run_output = agent.run(history_input, session_id=session_id)

                response_text = None
                if run_output and hasattr(run_output, "content") and run_output.content:
                    response_text = run_output.content
                if response_text is None and run_output and hasattr(run_output, "messages") and run_output.messages:
                    for m in reversed(run_output.messages):
                        if getattr(m, "content", None):
                            response_text = str(m.content)
                            break
                if response_text is None:
                    response_text = "No response generated."

                if _mongo_available and session_id and effective_agent_id:
                    try:
                        append_messages(session_id, effective_agent_id, [
                            {"role": "user", "content": message},
                            {"role": "assistant", "content": response_text},
                        ])
                    except Exception:
                        pass

                return response_text
            except Exception as e:
                last_error = e
                if is_retryable_gemini_error(e) and idx < len(keys) - 1:
                    continue
                raise
        if last_error:
            raise last_error
        raise ValueError("No Gemini API key set. Add GOOGLE_API_KEY or GEMINI_API_KEY in .env")
    finally:
        for k, v in saved_gemini.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for k in injected_env:
            if injected_env[k] is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = injected_env[k]
