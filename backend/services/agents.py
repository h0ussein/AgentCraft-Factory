# services/agents.py
# Agent listing: DB-backed with graceful fallback when MongoDB is not configured.

from typing import Any

from bson import ObjectId

from config.db import get_db_if_connected


def list_agents_from_db() -> list[dict[str, Any]]:
    """
    List all agents from MongoDB using the single connection from startup only.
    Returns [] if not connected (no second connection, no env read on request).
    """
    db = get_db_if_connected()
    if db is None:
        return []
    try:
        agents_col = db.agents
        tools_col = db.tools
    except Exception:
        return []
    try:
        agents = list(agents_col.find({}))
        result = []
        for a in agents:
            aid = str(a["_id"])
            tool_ids = a.get("tools") or []
            tool_docs = (
                list(tools_col.find({"_id": {"$in": [ObjectId(t) for t in tool_ids]}}))
                if tool_ids
                else []
            )
            result.append({
                "id": aid,
                "name": a.get("name") or "Unnamed Agent",
                "system_instruction": a.get("system_instruction") or "",
                "model_id": a.get("model_id") or "gemini-2.5-flash",
                "tools": [
                    {"id": str(t["_id"]), "name": t.get("name") or "tool"}
                    for t in tool_docs
                ],
            })
        return result
    except Exception:
        return []
