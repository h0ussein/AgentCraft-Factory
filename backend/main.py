# main.py
# FastAPI entry point for the Dynamic AI Agent Factory mobile web app

import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Always load .env from backend folder (no dependence on process cwd)
load_dotenv(Path(__file__).resolve().parent / ".env")

# Import tools manager and agent factory
from tools_manager import (
    create_tool_file,
    list_tool_files,
    extract_api_key_requirements,
    generate_tool_code_and_keys,
    write_tool_file,
)
from agent_factory import run_agent_chat
from services.agent_manager import run_agent_chat_genai
from config.db import get_db_if_connected
from config.gemini_keys import get_gemini_api_keys, ALLOWED_GEMINI_MODELS
from services.agents import list_agents_from_db
from models.chat_history import list_all_sessions, get_session_history, delete_session, delete_all_sessions_for_agent

# MongoDB: try to connect first on startup, then close on shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    from config.db import try_connect_mongodb
    ok, msg = try_connect_mongodb()
    if ok:
        print(msg)
        try:
            from models.agent import ensure_default_agent
            ensure_default_agent()
        except Exception as e:
            print(f"Default agent setup: {e}")
    else:
        print(f"MongoDB skipped: {msg}")
    yield
    try:
        from config.db import close
        close()
    except Exception:
        pass


app = FastAPI(
    title="Dynamic AI Agent Factory",
    description="Create tools from natural language and chat with an AI agent that uses them.",
    lifespan=lifespan,
)

# Same server serves API + built frontend (localhost:8000 and production)
IS_PRODUCTION = os.getenv("NODE_ENV") == "production" or os.getenv("ENV") == "production"
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
HAS_FRONTEND_BUILD = FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists()

# API under /api so SPA routes like /agents can be served as index.html
api = APIRouter()


class ProductionRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP -> HTTPS and www -> non-www in production (e.g. behind Render)."""
    async def dispatch(self, request, call_next):
        if not IS_PRODUCTION:
            return await call_next(request)
        host = request.headers.get("host", "")
        proto = request.headers.get("x-forwarded-proto", request.scope.get("scheme", "http"))
        path = request.url.path
        query = (request.url.query or "").strip()
        url = f"{path}?{query}" if query else path
        if proto == "http":
            return RedirectResponse(url=f"https://{host}{url}", status_code=301)
        if host.startswith("www."):
            non_www = host.replace("www.", "", 1)
            return RedirectResponse(url=f"https://{non_www}{url}", status_code=301)
        return await call_next(request)


app.add_middleware(ProductionRedirectMiddleware)
# CORS: only in development (frontend on different port); production = same origin, no CORS
if not IS_PRODUCTION:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# --- Request/Response models ---

class CreateToolRequest(BaseModel):
    """Request body for POST /create-tool"""
    prompt: str = Field(..., description="Natural language description of the tool to create")
    tool_name: str | None = Field(None, description="Optional filename for the tool (e.g. 'weather')")
    agent_id: str | None = Field(None, description="Optional agent _id to link this tool to (MongoDB)")
    user_id: str | None = Field(None, description="Optional user _id for storing resolved API keys")


class CreateToolResponse(BaseModel):
    """Response after creating a tool"""
    success: bool = True
    message: str = "Tool created successfully."
    file_path: str = Field(..., description="Path to the generated .py file")
    file_name: str = Field(..., description="Name of the file (e.g. tool_weather.py)")


class ChatRequest(BaseModel):
    """Request body for POST /chat"""
    message: str = Field(..., description="User message to send to the agent")
    session_id: str | None = Field(None, description="Optional session ID for conversation history (MongoDB memory)")
    agent_id: str | None = Field(None, description="Optional agent _id to use (loads only tools linked to this agent)")
    user_id: str | None = Field(None, description="Optional user _id for API key injection and validation from User document")


class ChatResponse(BaseModel):
    """Response from the agent"""
    response: str = Field(..., description="Agent's reply")
    session_id: str | None = Field(None, description="Session ID used (if any)")


class AgentToolRef(BaseModel):
    """Tool reference in agent list"""
    id: str
    name: str


class AgentListItem(BaseModel):
    """One agent in GET /agents response"""
    id: str
    name: str
    system_instruction: str = ""
    model_id: str = "gemini-2.5-flash"
    tools: list[AgentToolRef] = []


class AgentsListResponse(BaseModel):
    """Response for GET /agents"""
    agents: list[AgentListItem] = []
    count: int = 0


class CreateAgentRequest(BaseModel):
    """Request body for POST /agents"""
    name: str = Field(..., min_length=1, description="Agent display name")
    system_instruction: str = Field("", description="Optional system prompt")
    model_id: str = Field("gemini-2.5-flash", description="LLM model identifier")


class CreateAgentResponse(BaseModel):
    """Response after creating an agent"""
    id: str = Field(..., description="New agent _id")
    name: str = ""
    message: str = "Agent created."


# --- Endpoints ---

@app.get("/")
def root():
    """Serve frontend SPA when built; else API info."""
    if HAS_FRONTEND_BUILD:
        return FileResponse(str(FRONTEND_DIST / "index.html"))
    return {
        "app": "Dynamic AI Agent Factory",
        "endpoints": {
            "GET /agents": "List all agents from DB with their tools",
            "POST /agents": "Create a new agent",
            "POST /create-tool": "Generate a new tool from a natural language prompt",
            "POST /chat": "Send a message to the dynamic agent and get a response",
            "GET /tools": "List generated tool files",
        },
        "hint": "Run: npm run build (in project root) then restart backend. Or: npm run serve",
    }


@api.get("/health")
def health():
    """Health check; lists registered route paths so you can confirm /agents is loaded."""
    routes = [r.path for r in app.routes if hasattr(r, "path") and r.path.startswith("/")]
    return {"status": "ok", "routes": sorted(routes)}


@api.post("/create-tool", response_model=CreateToolResponse)
def create_tool(request: CreateToolRequest):
    """
    Generate a new Python tool only if every required API key is available:
    from Admin-stored APIs or from a detected public API. Otherwise returns 400.
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required.")
    if not get_gemini_api_keys():
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY or GEMINI_API_KEY is not set. Add in .env",
        )
    try:
        code, base_name, required_api_keys, public_api_keys = generate_tool_code_and_keys(
            user_description=request.prompt.strip(),
            tool_name=request.tool_name.strip() if request.tool_name else None,
        )
        # Resolve keys: (1) admin-stored APIs, (2) public key search (Gemini) for this tool
        resolved = {}
        try:
            from models.admin_api import get_admin_api_values_for_keys
            resolved = get_admin_api_values_for_keys(required_api_keys)
        except Exception:
            pass
        for k in required_api_keys:
            if k not in resolved or not resolved[k]:
                resolved[k] = (public_api_keys.get(k) or "").strip() or None
        missing = [k for k in required_api_keys if not resolved.get(k)]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=(
                    "We couldn't find an API key for this tool. We checked Admin APIs and searched for a public key. Required: "
                    + ", ".join(missing)
                    + ". Add them in Admin → APIs, or use a service that offers a public API."
                ),
            )
        # All keys resolved: write file and register tool
        path = write_tool_file(code, base_name)
        from models.tool import create_tool_doc
        from models.agent import get_agent_collection
        from models.user import ensure_user, set_user_api_key
        from bson import ObjectId

        tool_id = create_tool_doc(
            name=path.stem,
            description=request.prompt.strip()[:500],
            file_path=str(path),
            owner_agent_id=request.agent_id,
            required_api_keys=required_api_keys,
            public_api_keys=resolved,
        )
        if request.user_id:
            try:
                ensure_user(request.user_id)
                for key_name, key_value in resolved.items():
                    if key_value:
                        set_user_api_key(request.user_id, key_name, key_value)
            except Exception:
                pass
        if request.agent_id:
            get_agent_collection().update_one(
                {"_id": ObjectId(request.agent_id)},
                {"$push": {"tools": tool_id}},
            )
        else:
            first = get_agent_collection().find_one()
            if first:
                get_agent_collection().update_one(
                    {"_id": first["_id"]},
                    {"$push": {"tools": tool_id}},
                )
        message = "Tool created. You can use it in /chat."
        if resolved:
            message += " Keys used: " + ", ".join(resolved.keys()) + "."
        return CreateToolResponse(
            success=True,
            message=message,
            file_path=str(path),
            file_name=path.name,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from config.gemini_keys import is_retryable_gemini_error
        if is_retryable_gemini_error(e):
            raise HTTPException(
                status_code=429,
                detail="The AI service is currently at capacity. Please try again in a few moments. If this persists, the API quota may have been exceeded."
            )
        raise HTTPException(status_code=500, detail=f"Tool generation failed: {e}")


@api.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Send a message to the dynamic agent. The agent uses all loaded tools from custom_tools/.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="message is required.")
    if not get_gemini_api_keys():
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY or GEMINI_API_KEY is not set. Add in .env",
        )
    try:
        effective_agent_id = request.agent_id
        if not effective_agent_id and get_db_if_connected():
            first = get_db_if_connected().agents.find_one()
            if first:
                effective_agent_id = str(first["_id"])
        if effective_agent_id:
            response_text = run_agent_chat_genai(
                message=request.message.strip(),
                session_id=request.session_id,
                agent_id=effective_agent_id,
                user_id=request.user_id,
            )
        else:
            response_text = run_agent_chat(
                message=request.message.strip(),
                session_id=request.session_id,
                agent_id=request.agent_id,
                user_id=request.user_id,
            )
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
        )
    except Exception as e:
        # Check if it's a quota/rate limit error
        from config.gemini_keys import is_retryable_gemini_error
        if is_retryable_gemini_error(e):
            raise HTTPException(
                status_code=429,
                detail="The AI service is currently at capacity. Please try again in a few moments. If this persists, the API quota may have been exceeded."
            )
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


@api.get("/tools")
def list_tools(agent_id: str | None = None):
    """
    List tools. If agent_id is provided, returns only tools attached to that agent (from DB).
    If agent_id is omitted, returns all tool files from disk (legacy; prefer agent-scoped when possible).
    """
    if agent_id:
        try:
            from models.agent import get_agent_by_id
            from models.tool import get_tools_by_ids
            from bson import ObjectId
            agent_doc = get_agent_by_id(agent_id)
            if not agent_doc or not agent_doc.get("tools"):
                return {"count": 0, "files": []}
            tool_docs = get_tools_by_ids(agent_doc["tools"])
            files = [
                {"name": t.get("name") or "tool", "path": t.get("file_path") or "", "id": str(t["_id"])}
                for t in tool_docs
            ]
            return {"count": len(files), "files": files}
        except Exception:
            return {"count": 0, "files": []}
    files = list_tool_files()
    return {
        "count": len(files),
        "files": [{"name": p.stem, "path": str(p)} for p in files],
    }


@api.get("/agents", response_model=AgentsListResponse)
def list_agents():
    """
    List all agents from DB with their attached tools.
    Returns empty list when MongoDB is not configured (no 500).
    """
    agents = list_agents_from_db()
    return AgentsListResponse(agents=agents, count=len(agents))


@api.get("/sessions")
def list_sessions(agent_id: str | None = None):
    """
    List all chat sessions, optionally filtered by agent_id.
    Returns empty list when MongoDB is not configured (no 500).
    """
    try:
        db = get_db_if_connected()
        if db is None:
            return {"sessions": [], "count": 0}
        sessions = list_all_sessions(agent_id=agent_id)
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        # Graceful fallback if MongoDB not available
        return {"sessions": [], "count": 0}


@api.get("/sessions/{session_id}/history")
def get_chat_history_endpoint(session_id: str, agent_id: str | None = None):
    """
    Get full chat history for a session.
    Returns 404 if session not found, empty list if MongoDB not configured.
    """
    try:
        db = get_db_if_connected()
        if db is None:
            return {"session_id": session_id, "agent_id": agent_id, "messages": []}
        history = get_session_history(session_id, agent_id=agent_id)
        if not history:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "session_id": history.get("session_id"),
            "agent_id": history.get("agent_id"),
            "messages": history.get("messages", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        # Graceful fallback
        return {"session_id": session_id, "agent_id": agent_id, "messages": []}


@api.post("/agents", response_model=CreateAgentResponse)
def create_agent(request: CreateAgentRequest):
    """Create a new agent. Uses the same DB connection as startup."""
    db = get_db_if_connected()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="MongoDB not connected. Set MONGO_URI in .env and restart.",
        )
    name = (request.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    raw_model = (request.model_id or "gemini-2.5-flash").strip()
    model_id = raw_model if raw_model in ALLOWED_GEMINI_MODELS else "gemini-2.5-flash"
    doc = {
        "name": name,
        "system_instruction": (request.system_instruction or "").strip(),
        "model_id": model_id,
        "tools": [],
    }
    try:
        result = db.agents.insert_one(doc)
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        raise HTTPException(
            status_code=503,
            detail="MongoDB unavailable. Please try again later.",
        ) from e
    return CreateAgentResponse(id=str(result.inserted_id), name=name)


def _require_admin_passcode(x_admin_passcode: str | None) -> None:
    """Raise 403 if passcode missing or wrong, 503 if ADMIN_PASSCODE not set."""
    admin_passcode = (os.getenv("ADMIN_PASSCODE") or "").strip()
    if not admin_passcode:
        raise HTTPException(status_code=503, detail="ADMIN_PASSCODE not set in .env")
    if not x_admin_passcode or x_admin_passcode.strip() != admin_passcode:
        raise HTTPException(status_code=403, detail="Invalid admin passcode")


@api.get("/admin/verify")
def admin_verify(x_admin_passcode: str | None = Header(None, alias="X-Admin-Passcode")):
    """Verify admin passcode. Returns 200 if correct, 403 if wrong. Used to unlock Admin UI."""
    _require_admin_passcode(x_admin_passcode)
    return {"ok": True}


class CreateAdminApiRequest(BaseModel):
    """Request body for POST /admin/apis"""
    description: str = Field("", description="What this API is for (e.g. OpenWeatherMap for weather)")
    key_name: str = Field(..., description="Env key name tools use, e.g. OPENWEATHER_API_KEY")
    key_value: str = Field(..., description="The API key value")


@api.get("/admin/apis")
def list_admin_apis(x_admin_passcode: str | None = Header(None, alias="X-Admin-Passcode")):
    """List admin-defined APIs (for tool creation). Requires admin passcode."""
    _require_admin_passcode(x_admin_passcode)
    try:
        from models.admin_api import list_admin_apis as _list
        return {"apis": _list()}
    except Exception as e:
        if get_db_if_connected() is None:
            raise HTTPException(status_code=503, detail="MongoDB not connected")
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/admin/apis")
def create_admin_api(
    request: CreateAdminApiRequest,
    x_admin_passcode: str | None = Header(None, alias="X-Admin-Passcode"),
):
    """Create or update an admin-defined API key. Used when users create tools that need this key."""
    _require_admin_passcode(x_admin_passcode)
    try:
        from models.admin_api import create_admin_api as _create
        api_id = _create(
            description=request.description.strip(),
            key_name=request.key_name.strip(),
            key_value=request.key_value.strip(),
        )
        return {"ok": True, "id": api_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if get_db_if_connected() is None:
            raise HTTPException(status_code=503, detail="MongoDB not connected")
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/admin/tools")
def list_admin_tools(x_admin_passcode: str | None = Header(None, alias="X-Admin-Passcode")):
    """List all tools (from DB) for admin with agent name. Requires admin passcode."""
    _require_admin_passcode(x_admin_passcode)
    try:
        from models.tool import list_all_tools
        from bson import ObjectId
        tools = list_all_tools()
        db = get_db_if_connected()
        if db is not None:
            for t in tools:
                aid = t.get("owner_agent_id")
                if aid:
                    try:
                        agent = db.agents.find_one({"_id": ObjectId(aid)})
                        t["agent_name"] = (agent.get("name") or "—") if agent else "—"
                    except Exception:
                        t["agent_name"] = "—"
                else:
                    t["agent_name"] = "—"
        else:
            for t in tools:
                t["agent_name"] = "—"
        return {"tools": tools}
    except Exception as e:
        if get_db_if_connected() is None:
            raise HTTPException(status_code=503, detail="MongoDB not connected")
        raise HTTPException(status_code=500, detail=str(e))


@api.delete("/admin/tools/{tool_id}")
def delete_admin_tool(
    tool_id: str,
    x_admin_passcode: str | None = Header(None, alias="X-Admin-Passcode"),
):
    """Delete a tool (DB doc, references on agents, and file on disk). Requires admin passcode."""
    _require_admin_passcode(x_admin_passcode)
    try:
        from models.tool import delete_tool_by_id
        ok, file_path = delete_tool_by_id(tool_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Tool not found")
        if file_path and Path(file_path).exists():
            Path(file_path).unlink(missing_ok=True)
        return {"ok": True, "message": "Tool deleted"}
    except HTTPException:
        raise
    except Exception as e:
        if get_db_if_connected() is None:
            raise HTTPException(status_code=503, detail="MongoDB not connected")
        raise HTTPException(status_code=500, detail=str(e))


@api.delete("/agents/{agent_id}")
def delete_agent(
    agent_id: str,
    x_admin_passcode: str | None = Header(None, alias="X-Admin-Passcode"),
):
    """Delete an agent and all related chat sessions. Requires X-Admin-Passcode header to match ADMIN_PASSCODE in .env."""
    _require_admin_passcode(x_admin_passcode)
    db = get_db_if_connected()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    from bson import ObjectId
    try:
        oid = ObjectId(agent_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid agent id")
    try:
        # First, delete all chat sessions associated with this agent
        deleted_sessions_count = delete_all_sessions_for_agent(agent_id)
        
        # Then delete the agent
        result = db.agents.delete_one({"_id": oid})
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        raise HTTPException(
            status_code=503,
            detail="MongoDB unavailable. Please try again later.",
        ) from e
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "ok": True,
        "message": f"Agent deleted. {deleted_sessions_count} related chat session(s) also deleted."
    }


@api.delete("/sessions/{session_id}")
def delete_session_endpoint(
    session_id: str,
    agent_id: str | None = None,
    x_admin_passcode: str | None = Header(None, alias="X-Admin-Passcode"),
):
    """Delete a chat session. Requires X-Admin-Passcode header to match ADMIN_PASSCODE in .env."""
    _require_admin_passcode(x_admin_passcode)
    db = get_db_if_connected()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    try:
        deleted = delete_session(session_id, agent_id=agent_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {e}")
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True, "message": "Session deleted"}


app.include_router(api, prefix="/api")

# --- Serve built frontend (static + SPA fallback) when frontend/dist exists ---
if HAS_FRONTEND_BUILD:
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Serve index.html for non-API paths so SPA routing works."""
        return FileResponse(str(FRONTEND_DIST / "index.html"))


# Run server from backend folder: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
