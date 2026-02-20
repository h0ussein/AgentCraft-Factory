# models/user.py
# User schema: user_id, api_keys (for tool API key validation)

from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field

from config.db import get_db


class UserModel(BaseModel):
    """User document schema."""
    user_id: str = Field(..., description="Unique user identifier")
    api_keys: dict = Field(default_factory=dict, description="KEY_NAME -> value for tools that use os.getenv(KEY_NAME)")

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


def get_user_collection():
    """Get the users collection."""
    return get_db().users


def get_user(user_id: str) -> Optional[dict]:
    """Fetch user by user_id."""
    col = get_user_collection()
    return col.find_one({"user_id": user_id})


def get_user_api_keys(user_id: str) -> dict:
    """Get api_keys dict for user."""
    user = get_user(user_id)
    if not user:
        return {}
    return user.get("api_keys") or {}


def ensure_user(user_id: str) -> dict:
    """Create user document if not exists."""
    col = get_user_collection()
    doc = col.find_one({"user_id": user_id})
    if doc:
        return doc
    col.insert_one({"user_id": user_id, "api_keys": {}})
    return col.find_one({"user_id": user_id})


def set_user_api_key(user_id: str, key_name: str, value: str):
    """Set one API key for user."""
    col = get_user_collection()
    col.update_one(
        {"user_id": user_id},
        {"$set": {f"api_keys.{key_name}": value}},
        upsert=True,
    )
