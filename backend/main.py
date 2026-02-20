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
from tools_manager import create_tool_file, list_tool_files
from agent_factory import run_agent_chat
from config.db import get_db_if_connected
from config.gemini_keys import get_gemini_api_keys
from services.agents import list_agents_from_db
from models.chat_history import list_all_sessions, get_session_history

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
    Generate a new Python tool from a natural language description using Gemini 2.5 Flash.
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required.")
    if not get_gemini_api_keys():
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY or GEMINI_API_KEY is not set. Add in .env",
        )
    try:
        path = create_tool_file(
            user_description=request.prompt.strip(),
            tool_name=request.tool_name.strip() if request.tool_name else None,
        )
        # Optionally register tool in MongoDB and link to agent
        try:
            from models.tool import create_tool_doc
            from models.agent import get_agent_collection
            from bson import ObjectId
            tool_id = create_tool_doc(
                name=path.stem,
                description=request.prompt.strip()[:500],
                file_path=str(path),
                owner_agent_id=request.agent_id,
            )
            if request.agent_id:
                get_agent_collection().update_one(
                    {"_id": ObjectId(request.agent_id)},
                    {"$push": {"tools": tool_id}},
                )
            else:
                # Add to default agent (first one)
                first = get_agent_collection().find_one()
                if first:
                    get_agent_collection().update_one(
                        {"_id": first["_id"]},
                        {"$push": {"tools": tool_id}},
                    )
        except Exception:
            pass
        return CreateToolResponse(
            success=True,
            message="Tool created. You can use it in /chat.",
            file_path=str(path),
            file_name=path.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Check if it's a quota/rate limit error
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
def list_tools():
    """List generated tool files."""
    files = list_tool_files()
    return {
        "count": len(files),
        "files": [{"name": p.name, "path": str(p)} for p in files],
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
    doc = {
        "name": name,
        "system_instruction": (request.system_instruction or "").strip(),
        "model_id": (request.model_id or "gemini-2.5-flash").strip(),
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


@api.get("/admin/verify")
def admin_verify(x_admin_passcode: str | None = Header(None, alias="X-Admin-Passcode")):
    """Verify admin passcode. Returns 200 if correct, 403 if wrong. Used to unlock Admin UI."""
    admin_passcode = (os.getenv("ADMIN_PASSCODE") or "").strip()
    if not admin_passcode:
        raise HTTPException(status_code=503, detail="ADMIN_PASSCODE not set in .env")
    if not x_admin_passcode or x_admin_passcode.strip() != admin_passcode:
        raise HTTPException(status_code=403, detail="Invalid admin passcode")
    return {"ok": True}


@api.delete("/agents/{agent_id}")
def delete_agent(
    agent_id: str,
    x_admin_passcode: str | None = Header(None, alias="X-Admin-Passcode"),
):
    """Delete an agent. Requires X-Admin-Passcode header to match ADMIN_PASSCODE in .env."""
    admin_passcode = (os.getenv("ADMIN_PASSCODE") or "").strip()
    if not admin_passcode:
        raise HTTPException(
            status_code=503,
            detail="Admin delete not configured. Set ADMIN_PASSCODE in .env",
        )
    if not x_admin_passcode or x_admin_passcode.strip() != admin_passcode:
        raise HTTPException(status_code=403, detail="Invalid admin passcode")
    db = get_db_if_connected()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    from bson import ObjectId
    try:
        oid = ObjectId(agent_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid agent id")
    try:
        result = db.agents.delete_one({"_id": oid})
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        raise HTTPException(
            status_code=503,
            detail="MongoDB unavailable. Please try again later.",
        ) from e
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True, "message": "Agent deleted"}


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
