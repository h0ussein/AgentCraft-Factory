# config/db.py
# MongoDB connection (Python equivalent of Mongoose connection)

import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_client: MongoClient | None = None
_db: Database | None = None

# Try several .env locations so we find it regardless of cwd
_ENV_PATHS = [
    _BACKEND_DIR / ".env",
    Path.cwd() / ".env",
    Path.cwd() / "backend" / ".env",
]


def _load_env_anywhere() -> None:
    """Load .env from first path that exists."""
    for p in _ENV_PATHS:
        if p.exists():
            load_dotenv(p)
            break
    load_dotenv()  # also default (cwd) for good measure


def _get_mongo_uri() -> str:
    """Read MONGO_URI from env; load .env from multiple locations if missing."""
    _load_env_anywhere()
    uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
    return (uri or "").strip()


def _atlas_client_kwargs(uri: str) -> dict:
    """Options for MongoDB Atlas (certifi CA bundle). PyMongo does not support ssl_context."""
    kwargs = {"serverSelectionTimeoutMS": 20000}
    if "mongodb+srv" in (uri.split("?")[0] or ""):
        kwargs["tls"] = True
        try:
            import certifi
            kwargs["tlsCAFile"] = certifi.where()
        except ImportError:
            pass
    return kwargs


def try_connect_mongodb() -> tuple[bool, str]:
    """
    Try to connect to MongoDB first. Call at startup.
    Returns (True, "MongoDB connected") or (False, error_message).
    """
    _load_env_anywhere()
    uri = (os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "").strip()
    if not uri:
        return False, "MONGO_URI (or MONGODB_URI) not set. Put it in backend/.env"
    try:
        kwargs = _atlas_client_kwargs(uri)
        client = MongoClient(uri, **kwargs)
        db = client.get_default_database(default="agent_factory")
        db.command("ping")
        global _client, _db
        _client = client
        _db = db
        return True, "MongoDB connected"
    except Exception as e:
        return False, f"MongoDB connection failed: {e!s}"


def get_db_if_connected() -> Database | None:
    """Return the DB if already connected at startup; else None. Use this to avoid re-reading env on requests."""
    return _db


def get_client() -> MongoClient:
    """Get or create MongoDB client."""
    global _client
    if _client is None:
        uri = _get_mongo_uri()
        if not uri:
            raise ValueError(
                "MONGO_URI (or MONGODB_URI) is not set. Add the URI in .env"
            )
        kwargs = _atlas_client_kwargs(uri)
        _client = MongoClient(uri, **kwargs)
    return _client


def get_db(db_name: str | None = None) -> Database:
    """Get database instance. Uses database from MONGO_URI path only."""
    global _db
    if _db is None:
        client = get_client()
        _db = client.get_default_database(default="agent_factory") if db_name is None else client[db_name]
    return _db


def connect() -> Database:
    """Connect at startup; use try_connect_mongodb() for clear success/failure."""
    ok, msg = try_connect_mongodb()
    if not ok:
        raise RuntimeError(msg)
    return _db


def close():
    """Close the MongoDB connection."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        print("MongoDB connection closed")
