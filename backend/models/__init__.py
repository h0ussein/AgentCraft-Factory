# models package – MongoDB document helpers
from .agent import AgentModel, get_agent_collection, get_agent_by_id, ensure_default_agent
from .tool import ToolModel, get_tool_collection, get_tools_by_ids, create_tool_doc, get_tool_by_id
from .chat_history import (
    ChatHistoryModel,
    get_chat_history_collection,
    get_last_messages,
    append_messages,
    get_or_create_chat_history,
)
from .user import UserModel, get_user_collection, get_user, get_user_api_keys, ensure_user, set_user_api_key

__all__ = [
    "AgentModel",
    "get_agent_collection",
    "get_agent_by_id",
    "ensure_default_agent",
    "ToolModel",
    "get_tool_collection",
    "get_tools_by_ids",
    "create_tool_doc",
    "get_tool_by_id",
    "ChatHistoryModel",
    "get_chat_history_collection",
    "get_last_messages",
    "append_messages",
    "get_or_create_chat_history",
    "UserModel",
    "get_user_collection",
    "get_user",
    "get_user_api_keys",
    "ensure_user",
    "set_user_api_key",
]
