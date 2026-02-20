# Dynamic AI Agent Factory - Project Summary

## Project Overview
A full-stack mobile web application for creating and managing AI agents with dynamic tool generation. The system allows users to create AI agents, generate custom Python tools from natural language descriptions, and chat with agents that use these tools. Built with FastAPI backend, React frontend, MongoDB for persistence, and Gemini 2.5 Flash for AI capabilities.

---

## Task 1: Chat Screen (`ChatScreen.jsx`)
**Location:** `frontend/src/components/ChatScreen.jsx`

**Features:**
- Real-time chat interface with AI agents
- Message display with user messages (purple, right-aligned) and agent messages (dark grey, left-aligned)
- Header showing selected agent name or "Assistant Agent" with online status indicator
- Fixed session ID: "mobile-session-1" for conversation continuity
- Auto-scroll to bottom when new messages arrive
- Loading spinner animation (3 bouncing dots) while agent is processing
- Input form with text field, attach button, voice button, and send button
- Error handling with error messages displayed in chat
- Welcome message on initial load
- Responsive design with mobile-first approach (max-width: 428px)
- Safe area bottom padding for mobile devices
- Back button and menu button in header (UI only, not functional)
- Today's date and time display at top of messages
- Purple theme with dark slate background

**API Integration:**
- Uses `sendChat()` from `api.js` to POST to `/api/chat`
- Supports optional `agentId` and `sessionId` parameters
- Handles API errors gracefully

---

## Task 2: My Agents Screen (`MyAgentsScreen.jsx`)
**Location:** `frontend/src/components/MyAgentsScreen.jsx`

**Features:**
- Lists all agents from MongoDB database
- Agent cards display:
  - Agent name (truncated if too long)
  - Model ID (e.g., "gemini-2.5-flash")
  - List of attached tools as badges
  - Purple agent icon
  - "Chat →" indicator
- Clicking an agent card selects it and navigates to Chat screen
- Loading state with animated bouncing dots
- Empty state message when no agents exist
- Error state with red error message display
- Glassmorphism design with backdrop blur
- Responsive card layout with hover effects
- Tool badges show tool names in slate-colored pills
- "No tools assigned" message when agent has no tools

**API Integration:**
- Uses `listAgents()` from `api.js` to GET `/api/agents`
- Automatically refreshes when component mounts

---

## Task 3: Admin Screen (`AdminScreen.jsx`)
**Location:** `frontend/src/components/AdminScreen.jsx`

**Features:**
- **Passcode Protection:** Requires admin passcode (from `.env` ADMIN_PASSCODE) to unlock
- **Locked State:**
  - Password input field
  - "Unlock" button
  - Error message display for invalid passcode
  - "Back to app" link
- **Unlocked State:**
  - List of all agents with delete buttons
  - Agent display shows name and model_id
  - Red "Delete" button for each agent
  - "Deleting…" state while deletion is in progress
  - "Lock" button to return to locked state
  - Loading spinner while fetching agents
  - Empty state when no agents exist
- Amber/yellow theme for admin interface (different from main purple theme)
- Error messages displayed in red alert boxes
- Accessible via `/admin` route (not in main navigation)

**API Integration:**
- Uses `verifyAdminPasscode()` to POST to `/api/admin/verify` with X-Admin-Passcode header
- Uses `listAgents()` to GET `/api/agents`
- Uses `deleteAgent()` to DELETE `/api/agents/{agentId}` with passcode header

---

## Task 4: Create Tool Form (`CreateToolForm.jsx`)
**Location:** `frontend/src/components/CreateToolForm.jsx`

**Features:**
- Modal overlay with backdrop blur
- Large textarea for tool description (natural language prompt)
- Placeholder text: "Create a tool that fetches the current price of Bitcoin..."
- Agent dropdown selector to assign tool to specific agent
- Auto-loads agents list on mount
- Auto-selects first agent if available
- Loading state while agents are being fetched
- Error handling for agent loading failures
- Success message showing created file name
- "Create Tool" button (disabled when prompt is empty or loading)
- "Close" button to dismiss modal
- Form validation (prompt required)
- Loading state: "Creating…" while tool is being generated
- Responsive modal design (full-width on mobile, centered on desktop)
- Safe area bottom padding for mobile

**API Integration:**
- Uses `listAgents()` to populate agent dropdown
- Uses `createTool()` to POST to `/api/create-tool` with prompt, optional tool_name, and agent_id

**Backend Process:**
- Tool generation uses Gemini 2.5 Flash to generate Python code
- Safety review step validates generated code for malicious patterns
- Tool saved to `backend/custom_tools/` directory
- Tool document created in MongoDB `tools` collection
- Tool linked to selected agent in `agents` collection

---

## Task 5: Create Agent Form (`CreateAgentForm.jsx`)
**Location:** `frontend/src/components/CreateAgentForm.jsx`

**Features:**
- Modal overlay with backdrop blur
- Agent name input field (required, auto-focus)
- Placeholder: "e.g. Research Assistant"
- System instruction textarea (optional, 3 rows)
- Placeholder: "How this agent should behave..."
- Success state showing created agent name
- "Done" button after successful creation
- "Create" and "Cancel" buttons
- Form validation (name required)
- Loading state: "Creating…" while agent is being created
- Error message display
- Responsive modal design

**API Integration:**
- Uses `createAgent()` to POST to `/api/agents` with name, system_instruction, and model_id (defaults to "gemini-2.5-flash")

**Backend Process:**
- Agent document created in MongoDB `agents` collection
- Default model_id: "gemini-2.5-flash"
- Empty tools array initialized

---

## Task 6: Creation Modal (`CreationModal.jsx`)
**Location:** `frontend/src/components/CreationModal.jsx`

**Features:**
- Modal overlay triggered by "+" button in bottom navigation
- Two action cards:
  - **Create New Agent:** Purple-themed card with agent icon
    - Description: "Deploy an autonomous AI assistant with specific goals, memory, and persona."
  - **Create New Tool:** Cyan-themed card with tool icon
    - Description: "Configure a utility function, API connector, or scraper for your agents."
- Clicking a card closes modal and opens respective form
- Close button (X) in top right
- Pro tip message at bottom: "You can also use '/' commands in chat to quick-create."
- Responsive grid layout (1 column on mobile, 2 columns on desktop)
- Backdrop blur effect
- Safe area bottom padding

**User Flow:**
- User clicks "+" → Modal opens
- User selects "Create New Agent" → Opens CreateAgentForm
- User selects "Create New Tool" → Opens CreateToolForm

---

## Task 7: Bottom Navigation (`BottomNav.jsx`)
**Location:** `frontend/src/components/BottomNav.jsx`

**Features:**
- Fixed bottom navigation bar
- Three navigation items:
  - **Chat:** Chat bubble icon, navigates to Chat screen
  - **Add (+):** Large purple circular button with plus icon, opens CreationModal
  - **Agents:** Users icon, navigates to My Agents screen
- Active state highlighting (purple color for active tab)
- Inactive tabs in slate-gray
- Touch-friendly button sizes (min 44px height)
- Safe area bottom padding for mobile devices
- Backdrop blur effect
- Max-width constraint (428px) matching app container

---

## Task 8: Main App Component (`App.jsx`)
**Location:** `frontend/src/App.jsx`

**Features:**
- Root component managing application state and routing
- Tab state management: "chat" (default), "agents"
- Modal state management for CreationModal, CreateToolForm, CreateAgentForm
- Agent selection state (selectedAgent with id and name)
- Agents version counter for refresh triggers
- Route detection for admin screen (`/admin`)
- Conditional rendering:
  - Admin route → Shows AdminScreen only
  - Main app → Shows ChatScreen or MyAgentsScreen based on active tab
- Bottom navigation always visible (except on admin route)
- Modal overlays conditionally rendered
- Agent selection handler: selects agent and switches to chat tab
- Tool/agent creation success handlers
- Mobile-first responsive container (max-width: 428px, centered)

**State Management:**
- `tab`: Current active tab ("chat" or "agents")
- `modalOpen`: CreationModal visibility
- `toolFormOpen`: CreateToolForm visibility
- `agentFormOpen`: CreateAgentForm visibility
- `agentsVersion`: Counter to force refresh of MyAgentsScreen
- `selectedAgent`: Currently selected agent for chat

---

## Task 9: Backend API Endpoints (`main.py`)
**Location:** `backend/main.py`

**API Endpoints:**

1. **GET /** - Root endpoint
   - Serves frontend `index.html` if built, else returns API info JSON

2. **GET /api/health** - Health check
   - Returns status and list of registered routes

3. **POST /api/create-tool** - Create new tool
   - Request: `prompt` (required), `tool_name` (optional), `agent_id` (optional)
   - Generates Python tool using Gemini 2.5 Flash
   - Safety review validates generated code
   - Saves to `custom_tools/` directory
   - Creates tool document in MongoDB
   - Links tool to agent if agent_id provided
   - Returns: file_path, file_name, success message

4. **POST /api/chat** - Chat with agent
   - Request: `message` (required), `session_id` (optional), `agent_id` (optional), `user_id` (optional)
   - Loads agent from MongoDB if agent_id provided
   - Loads agent's tools from database
   - Syncs conversation history with MongoDB ChatHistory
   - Returns: response text, session_id

5. **GET /api/tools** - List tool files
   - Returns list of all `.py` files in `custom_tools/` directory

6. **GET /api/agents** - List all agents
   - Returns all agents from MongoDB with their attached tools
   - Graceful fallback if MongoDB not connected (returns empty list)

7. **POST /api/agents** - Create new agent
   - Request: `name` (required), `system_instruction` (optional), `model_id` (optional, defaults to "gemini-2.5-flash")
   - Creates agent document in MongoDB
   - Returns: agent id, name, success message

8. **DELETE /api/agents/{agent_id}** - Delete agent
   - Requires X-Admin-Passcode header matching ADMIN_PASSCODE env var
   - Deletes agent from MongoDB
   - Returns success message

9. **GET /api/admin/verify** - Verify admin passcode
   - Requires X-Admin-Passcode header
   - Returns 200 if correct, 403 if wrong

**Middleware:**
- CORS middleware (development only, allows localhost:5173, localhost:3000)
- Production redirect middleware (HTTP→HTTPS, www→non-www)
- Static file serving for frontend assets
- SPA fallback routing (all non-API routes serve index.html)

**Lifespan Events:**
- Startup: Attempts MongoDB connection, ensures default agent exists
- Shutdown: Closes MongoDB connection

---

## Task 10: Backend Core Services & Models

### Tool Generation (`tools_manager.py`)
**Location:** `backend/tools_manager.py`

**Features:**
- Generates Python tools from natural language using Gemini 2.5 Flash
- **Safety Review System:** Gemini reviews its own generated code for malicious patterns
- **Code Standards:**
  - Single Python function only (no classes, no `if __name__` blocks)
  - Type hints required
  - Docstring required
  - Only `os.getenv('KEY_NAME')` for API keys (no hardcoding)
  - Forbidden: file system access, subprocess, eval, exec, os.environ iteration
  - Allowed: requests, json, os.getenv for specific keys
- Filename sanitization (alphanumeric + underscore, max 40 chars)
- Unique filename generation (appends counter if file exists)
- Saves to `backend/custom_tools/` directory
- Retry logic with secondary API key on quota errors

### Agent Factory (`agent_factory.py`)
**Location:** `backend/agent_factory.py`

**Features:**
- Builds Agno Agent instances with tools
- **Agent Loading:**
  - Loads agent from MongoDB by agent_id
  - Loads only tools linked to agent (from Tool documents)
  - Loads tool functions from `custom_tools/` directory via file_path
- **Memory Management:**
  - Syncs chat history with MongoDB ChatHistory collection
  - Loads last 10 messages as context
  - Appends user + assistant messages after each run
- **API Key Validation:**
  - Wraps tools with validation function
  - Checks required API keys exist in User document or environment
  - Returns error message if keys missing
- **User API Key Injection:**
  - Injects user's API keys into environment for tool execution
  - Restores environment after execution
- **Fallback Behavior:**
  - If no agent_id: uses default config, optionally loads all custom_tools
  - If MongoDB unavailable: graceful degradation

### Database Models

**Agent Model (`models/agent.py`):**
- Schema: name, system_instruction, model_id, tools (array of Tool IDs)
- Functions: get_agent_by_id(), ensure_default_agent(), get_agent_collection()

**Tool Model (`models/tool.py`):**
- Schema: name, description, file_path, owner_agent_id
- Functions: create_tool_doc(), get_tools_by_ids(), get_tool_by_id()

**Database Connection (`config/db.py`):**
- MongoDB connection using MONGO_URI from .env
- Supports MongoDB Atlas (with SSL) and local MongoDB
- Graceful connection handling (try_connect_mongodb returns success/failure)
- Single connection pattern (get_db_if_connected for read-only checks)

**Agent Service (`services/agents.py`):**
- Lists agents from MongoDB with their tools
- Returns empty list if MongoDB not connected (no errors)
- Formats agent data with tool references

### API Client (`frontend/src/api.js`)
**Location:** `frontend/src/api.js`

**Functions:**
- `sendChat(message, sessionId, agentId)` - POST /api/chat
- `createTool(prompt, toolName, agentId)` - POST /api/create-tool
- `listAgents()` - GET /api/agents
- `createAgent(name, systemInstruction, modelId)` - POST /api/agents
- `listTools()` - GET /api/tools
- `verifyAdminPasscode(passcode)` - GET /api/admin/verify
- `deleteAgent(agentId, passcode)` - DELETE /api/agents/{agentId}

**Configuration:**
- API_BASE: `/api` in production, `http://localhost:8000/api` in development
- Error handling with detail messages from API responses

---

## Additional Project Details

### Environment Variables (`.env`)
- `GOOGLE_API_KEY` - Primary Gemini API key
- `GEMINI_API_KEY_SECONDARY` - Secondary Gemini API key (fallback)
- `MONGO_URI` - MongoDB connection string
- `ADMIN_PASSCODE` - Admin screen passcode (default: 301103)
- `NODE_ENV` - Environment mode (development/production)

### Project Structure
```
my_ai-project/
├── backend/
│   ├── main.py (FastAPI app)
│   ├── agent_factory.py (Agent building logic)
│   ├── tools_manager.py (Tool generation)
│   ├── config/
│   │   ├── db.py (MongoDB connection)
│   │   └── gemini_keys.py (API key management)
│   ├── models/
│   │   ├── agent.py (Agent schema)
│   │   ├── tool.py (Tool schema)
│   │   ├── chat_history.py (Chat history schema)
│   │   └── user.py (User schema)
│   ├── services/
│   │   └── agents.py (Agent listing service)
│   └── custom_tools/ (Generated tool files)
├── frontend/
│   ├── src/
│   │   ├── App.jsx (Main app component)
│   │   ├── api.js (API client)
│   │   └── components/
│   │       ├── ChatScreen.jsx
│   │       ├── MyAgentsScreen.jsx
│   │       ├── AdminScreen.jsx
│   │       ├── CreateToolForm.jsx
│   │       ├── CreateAgentForm.jsx
│   │       ├── CreationModal.jsx
│   │       └── BottomNav.jsx
│   └── dist/ (Built frontend files)
└── package.json (Build scripts)
```

### Technology Stack
- **Backend:** FastAPI, Python, MongoDB (PyMongo), Agno Agent Framework, Google Gemini API
- **Frontend:** React, Vite, Tailwind CSS
- **Database:** MongoDB Atlas
- **AI Model:** Google Gemini 2.5 Flash
- **Deployment:** Single server (FastAPI serves both API and static frontend)

### Security Features
- Tool code safety review before saving
- Sandboxed tool execution (RestrictedPython)
- API key validation against User documents
- Admin passcode protection
- No file system access in generated tools
- No code execution vulnerabilities (no eval, exec, subprocess)

### Mobile-First Design
- Fixed max-width container (428px)
- Touch-friendly button sizes (min 44px)
- Safe area padding for mobile devices
- Responsive modals (full-width on mobile, centered on desktop)
- Bottom navigation bar (mobile app style)

---

## Summary
This project is a complete AI agent management system with 4 main screens (Chat, My Agents, Admin, Creation Modals), 9 API endpoints, dynamic tool generation with safety validation, MongoDB persistence, and a mobile-first responsive UI. All components work together to enable users to create AI agents, generate custom tools from natural language, and chat with agents that use these tools.
