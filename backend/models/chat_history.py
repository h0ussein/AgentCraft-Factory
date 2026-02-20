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


def list_all_sessions(agent_id: str | None = None) -> list[dict]:
    """
    List all chat sessions, optionally filtered by agent_id.
    Returns sessions with metadata: session_id, agent_id, last_message_time, message_count, preview.
    Returns empty list if MongoDB is not connected.
    """
    try:
        col = get_chat_history_collection()
        query = {}
        if agent_id:
            agent_oid = str(agent_id) if isinstance(agent_id, ObjectId) else agent_id
            query["agent_id"] = agent_oid
        
        sessions = list(col.find(query))
        result = []
        for sess in sessions:
            messages = sess.get("messages", [])
            last_message = messages[-1] if messages else None
            last_message_time = last_message.get("timestamp") if last_message else sess.get("created_at", datetime.now(timezone.utc))
            
            # Get preview from last user message or last message
            preview = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    preview = msg.get("content", "")[:100]
                    break
            if not preview and last_message:
                preview = last_message.get("content", "")[:100]
            
            result.append({
                "session_id": sess.get("session_id"),
                "agent_id": sess.get("agent_id"),
                "last_message_time": last_message_time.isoformat() if isinstance(last_message_time, datetime) else str(last_message_time),
                "message_count": len(messages),
                "preview": preview,
            })
        
        # Sort by last_message_time descending (newest first)
        result.sort(key=lambda x: x["last_message_time"], reverse=True)
        return result
    except Exception:
        return []


def get_session_history(session_id: str, agent_id: str | None = None) -> dict | None:
    """
    Get full chat history for a session.
    Returns session document with all messages.
    Returns None if MongoDB is not connected or session not found.
    """
    try:
        col = get_chat_history_collection()
        query = {"session_id": session_id}
        if agent_id:
            agent_oid = str(agent_id) if isinstance(agent_id, ObjectId) else agent_id
            query["agent_id"] = agent_oid
        
        doc = col.find_one(query)
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
    except Exception:
        return None


def delete_session(session_id: str, agent_id: str | None = None) -> bool:
    """
    Delete a chat session.
    Returns True if deleted, False if not found.
    """
    try:
        col = get_chat_history_collection()
        query = {"session_id": session_id}
        if agent_id:
            agent_oid = str(agent_id) if isinstance(agent_id, ObjectId) else agent_id
            query["agent_id"] = agent_oid
        
        result = col.delete_one(query)
        return result.deleted_count > 0
    except Exception:
        return False


def delete_all_sessions_for_agent(agent_id: str) -> int:
    """
    Delete all chat sessions for a specific agent.
    Returns the number of sessions deleted.
    """
    try:
        col = get_chat_history_collection()
        agent_oid = str(agent_id) if isinstance(agent_id, ObjectId) else agent_id
        result = col.delete_many({"agent_id": agent_oid})
        return result.deleted_count
    except Exception:
        return 0
