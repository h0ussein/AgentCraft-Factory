# models/agent.py
# Agent schema: name, system_instruction, model_id, tools: [ToolID]

from typing import List
from bson import ObjectId
from pydantic import BaseModel, Field

from config.db import get_db


class AgentModel(BaseModel):
    """Agent document schema."""
    name: str = Field(..., description="Agent display name")
    system_instruction: str = Field("", description="System prompt / instructions")
    model_id: str = Field("gemini-2.5-flash", description="LLM model identifier")
    tools: List[str] = Field(default_factory=list, description="List of Tool _id (ObjectId as str)")

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


def get_agent_collection():
    """Get the agents collection."""
    return get_db().agents


def get_agent_by_id(agent_id: str | ObjectId):
    """Fetch one agent by _id."""
    col = get_agent_collection()
    oid = ObjectId(agent_id) if isinstance(agent_id, str) else agent_id
    doc = col.find_one({"_id": oid})
    return doc


def ensure_default_agent():
    """
    Ensure a default agent exists in the DB. Use on startup.
    """
    col = get_agent_collection()
    if col.count_documents({}) == 0:
        col.insert_one({
            "name": "Dynamic Assistant",
            "system_instruction": "You are a helpful AI assistant with access to tools. Always check your available tools and use them when they can help the user.",
            "model_id": "gemini-2.5-flash",
            "tools": [],
        })
        print("Default agent created in MongoDB")
