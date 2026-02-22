# models/admin_api.py
# Admin-defined APIs: key_name, description, key_value (used when creating tools)

from bson import ObjectId

from config.db import get_db


def get_admin_api_collection():
    """Collection for admin-defined API keys (key_name -> value for tool creation)."""
    return get_db().admin_apis


def get_admin_api_value(key_name: str) -> str | None:
    """Return stored value for an API key name, or None."""
    col = get_admin_api_collection()
    doc = col.find_one({"key_name": (key_name or "").strip()})
    if not doc:
        return None
    return (doc.get("key_value") or "").strip() or None


def get_admin_api_values_for_keys(key_names: list[str]) -> dict[str, str]:
    """Return dict of key_name -> value for all keys that are stored."""
    if not key_names:
        return {}
    col = get_admin_api_collection()
    cursor = col.find({"key_name": {"$in": [k.strip() for k in key_names if k]}})
    return {doc["key_name"]: (doc.get("key_value") or "").strip() for doc in cursor if (doc.get("key_value") or "").strip()}


def list_admin_apis():
    """List all admin-defined APIs (for admin UI). Returns list of {id, key_name, description, key_value_masked}."""
    col = get_admin_api_collection()
    out = []
    for doc in col.find({}).sort("key_name", 1):
        val = (doc.get("key_value") or "").strip()
        out.append({
            "id": str(doc["_id"]),
            "key_name": doc.get("key_name") or "",
            "description": doc.get("description") or "",
            "key_value_masked": "****" + val[-4:] if len(val) > 4 else "****",
        })
    return out


def create_admin_api(description: str, key_name: str, key_value: str) -> str:
    """Insert or update admin API. key_name is unique. Returns id."""
    key_name = (key_name or "").strip()
    description = (description or "").strip()
    key_value = (key_value or "").strip()
    if not key_name:
        raise ValueError("key_name is required")
    col = get_admin_api_collection()
    existing = col.find_one({"key_name": key_name})
    doc = {
        "key_name": key_name,
        "description": description,
        "key_value": key_value,
    }
    if existing:
        col.update_one({"_id": existing["_id"]}, {"$set": doc})
        return str(existing["_id"])
    result = col.insert_one(doc)
    return str(result.inserted_id)


def delete_admin_api(api_id: str) -> bool:
    """Delete an admin-defined API by id. Returns True if deleted, False if not found."""
    if not (api_id or "").strip():
        return False
    col = get_admin_api_collection()
    try:
        result = col.delete_one({"_id": ObjectId(api_id)})
        return result.deleted_count > 0
    except Exception:
        return False
