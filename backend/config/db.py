"""
Simple MongoDB connection using MONGO_URI from .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR / ".env")

_client = None
_db = None


def get_client() -> MongoClient:
    """Get MongoDB client. Creates connection if needed."""
    global _client
    if _client is None:
        uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
        if not uri:
            raise ValueError("MONGO_URI not set in backend/.env")
        # MongoDB Atlas SSL fix: add to URI string for Python 3.13 Windows compatibility
        if "mongodb+srv" in uri and "tlsAllowInvalidCertificates" not in uri:
            separator = "&" if "?" in uri else "?"
            uri = f"{uri}{separator}tlsAllowInvalidCertificates=true"
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    return _client


def get_db(db_name: str = "agent_factory") -> Database:
    """Get MongoDB database."""
    global _db
    if _db is None:
        client = get_client()
        _db = client[db_name]
    return _db


def get_db_if_connected() -> Database | None:
    """Get database if already connected, else None."""
    return _db


def try_connect_mongodb():
    """Try to connect at startup. Returns (True, msg) or (False, short_error)."""
    global _client, _db
    # Reset connection state to force fresh connection
    if _client:
        try:
            _client.close()
        except:
            pass
    _client = None
    _db = None
    
    try:
        db = get_db()
        db.command("ping")
        return True, "MongoDB connected"
    except Exception as e:
        # Reset on failure
        _client = None
        _db = None
        # Return short error message, not full traceback
        return False, "MongoDB not available"


def connect() -> Database:
    """Connect at startup; raises if connection fails."""
    ok, msg = try_connect_mongodb()
    if not ok:
        raise RuntimeError(msg)
    return _db


def close():
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
