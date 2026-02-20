# models/tool.py
# Tool schema: name, description, file_path, owner_agent_id

from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field

from config.db import get_db


class ToolModel(BaseModel):
    """Tool document schema."""
    name: str = Field(..., description="Tool name (e.g. file name without .py)")
    description: str = Field("", description="What the tool does")
    file_path: str = Field(..., description="Absolute or relative path to .py file")
    owner_agent_id: Optional[str] = Field(None, description="Agent _id that owns this tool")

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


def get_tool_collection():
    """Get the tools collection."""
    return get_db().tools


def get_tool_by_id(tool_id: str | ObjectId):
    """Fetch one tool by _id."""
    col = get_tool_collection()
    oid = ObjectId(tool_id) if isinstance(tool_id, str) else tool_id
    return col.find_one({"_id": oid})


def get_tools_by_ids(tool_ids: list[str | ObjectId]) -> list[dict]:
    """
    Fetch all tools whose _id is in tool_ids. Used when loading agent's tools.
    """
    if not tool_ids:
        return []
    col = get_tool_collection()
    oids = [ObjectId(t) if isinstance(t, str) else t for t in tool_ids]
    return list(col.find({"_id": {"$in": oids}}))


def create_tool_doc(name: str, description: str, file_path: str, owner_agent_id: str | None = None) -> str:
    """
    Insert a new tool document and return its _id as string.
    """
    col = get_tool_collection()
    doc = {
        "name": name,
        "description": description,
        "file_path": file_path,
        "owner_agent_id": owner_agent_id,
    }
    result = col.insert_one(doc)
    return str(result.inserted_id)
