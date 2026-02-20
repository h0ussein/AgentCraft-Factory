# models/chat_history.py
# ChatHistory schema: session_id, agent_id, messages: [{role, content, timestamp}]

from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from pydantic import BaseModel, Field

from config.db import get_db


class MessageItem(BaseModel):
    """Single message in chat history."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatHistoryModel(BaseModel):
    """Chat history document."""
    session_id: str = Field(..., description="Session identifier")
    agent_id: str = Field(..., description="Agent _id")
    messages: List[dict] = Field(default_factory=list, description="List of {role, content, timestamp}")

    class Config:
        arbitrary_types_allowed = True


def get_chat_history_collection():
    """Get the chat_histories collection."""
    return get_db().chat_histories


def get_or_create_chat_history(session_id: str, agent_id: str) -> dict:
    """Find or create a chat history for session + agent."""
    col = get_chat_history_collection()
    agent_oid = str(agent_id) if isinstance(agent_id, ObjectId) else agent_id
    doc = col.find_one({"session_id": session_id, "agent_id": agent_oid})
    if doc:
        return doc
    new_doc = {
        "session_id": session_id,
        "agent_id": agent_oid,
        "messages": [],
    }
    col.insert_one(new_doc)
    new_doc["_id"] = new_doc.get("_id")
    return col.find_one({"session_id": session_id, "agent_id": agent_oid})


def get_last_messages(session_id: str, agent_id: str, limit: int = 10) -> list[dict]:
    """
    Get the last `limit` messages for this session and agent (newest at end).
    """
    col = get_chat_history_collection()
    agent_oid = str(agent_id) if isinstance(agent_id, ObjectId) else agent_id
    doc = col.find_one({"session_id": session_id, "agent_id": agent_oid})
    if not doc or not doc.get("messages"):
        return []
    messages = doc["messages"]
    return list(messages[-limit:]) if len(messages) >= limit else list(messages)


def append_messages(session_id: str, agent_id: str, new_messages: list[dict]):
    """
    Append new messages to chat history. Each item: {role, content, timestamp}.
    """
    col = get_chat_history_collection()
    agent_oid = str(agent_id) if isinstance(agent_id, ObjectId) else agent_id
    for m in new_messages:
        if "timestamp" not in m:
            m["timestamp"] = datetime.now(timezone.utc)
    col.update_one(
        {"session_id": session_id, "agent_id": agent_oid},
        {"$push": {"messages": {"$each": new_messages}}},
        upsert=True,
    )
