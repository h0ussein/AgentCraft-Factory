# Dynamic AI Agent Factory

**Build AI agents, give them tools, and let them work for you.**

---

## The idea

Dynamic AI Agent Factory is a platform where you design AI agents and equip them with custom tools. You describe what you need in plain language; the system helps create the tools and attach them to your agents. Then you chat with those agents—they use the tools you gave them to search the web, run calculations, call APIs, or whatever you configured.

No need to write or deploy tool code yourself. You define agents, describe the tools they need, and the platform handles generation, safety checks, and execution so your agents can act on real data and services.

---

## What you can do

- **Create agents** — Name them, set their behavior, and choose the model they use.
- **Create tools** — Describe a tool in natural language (e.g. “search the web”, “get weather”, “convert units”). The system generates safe, runnable tools and links them to your agents. Web search uses a built-in integration with a leading search API.
- **Chat with agents** — Talk to an agent; it uses its tools in sequence when your request needs multiple steps (e.g. search, then calculate, then summarize).
- **Manage everything** — List agents and their tools, manage chat sessions, and use an admin area for cleanup and control.

Tools run in a sandbox, use only allowed APIs and environment keys, and are reviewed before use so agents stay safe and predictable.

---

## Getting started

1. Clone the repo and set up environment variables (see `.env.example`). You’ll need at least a Gemini API key and, if you use it, a key for the built-in web search.
2. Install dependencies and run the backend; build and serve the frontend, or run both in development.
3. Open the app, create an agent, create a tool (e.g. “search on web”), assign it to the agent, and start chatting.

The app works as a single deployable service: the same server serves the API and the web UI.

---

## Tech

Backend: **FastAPI**, **MongoDB**, **Google Gemini**. Frontend: **React**, **Vite**. Agents and tools are persisted so your agents and their capabilities stay available across sessions.

---

*Dynamic AI Agent Factory — agents and tools, defined by you.*
