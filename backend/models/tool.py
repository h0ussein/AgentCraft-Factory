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
    required_api_keys: list = Field(default_factory=list, description="List of API key names this tool requires (e.g. ['OPENWEATHER_API_KEY'])")
    public_api_keys: dict = Field(default_factory=dict, description="Detected public API keys {KEY_NAME: value} if available")

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
    Skips invalid IDs so one bad entry in DB does not break agent loading.
    """
    if not tool_ids:
        return []
    oids = []
    for t in tool_ids:
        try:
            oids.append(ObjectId(t) if isinstance(t, str) else t)
        except Exception:
            continue
    if not oids:
        return []
    col = get_tool_collection()
    return list(col.find({"_id": {"$in": oids}}))


def create_tool_doc(
    name: str, 
    description: str, 
    file_path: str, 
    owner_agent_id: str | None = None,
    required_api_keys: list | None = None,
    public_api_keys: dict | None = None,
) -> str:
    """
    Insert a new tool document and return its _id as string.
    
    Args:
        name: Tool name
        description: Tool description
        file_path: Path to tool file
        owner_agent_id: Optional agent ID that owns this tool
        required_api_keys: List of API key names this tool requires
        public_api_keys: Dict of detected public API keys {KEY_NAME: value}
    """
    col = get_tool_collection()
    doc = {
        "name": name,
        "description": description,
        "file_path": file_path,
        "owner_agent_id": owner_agent_id,
        "required_api_keys": required_api_keys or [],
        "public_api_keys": public_api_keys or {},
    }
    result = col.insert_one(doc)
    return str(result.inserted_id)
