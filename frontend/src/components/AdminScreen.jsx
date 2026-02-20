/**
 * Admin screen – passcode to unlock, then list agents and chats with Delete buttons
 */

import { useState, useEffect } from "react";
import { listAgents, verifyAdminPasscode, deleteAgent, listSessions, deleteSession } from "../api";

export default function AdminScreen() {
  const [passcode, setPasscode] = useState("");
  const [unlocked, setUnlocked] = useState(false);
  const [activeTab, setActiveTab] = useState("agents"); // "agents" or "chats"
  const [agents, setAgents] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    if (!unlocked) return;
    setLoading(true);
    setError(null);
    let cancelled = false;
    
    const loadData = async () => {
      try {
        if (activeTab === "agents") {
          const data = await listAgents();
          if (!cancelled) setAgents(data.agents || []);
        } else {
          const data = await listSessions();
          if (!cancelled) setSessions(data.sessions || []);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    
    loadData();
    return () => { cancelled = true; };
  }, [unlocked, activeTab]);

  async function handleUnlock(e) {
    e.preventDefault();
    if (!passcode.trim()) return;
    setError(null);
    try {
      await verifyAdminPasscode(passcode.trim());
      setUnlocked(true);
    } catch (err) {
      setError(err.message || "Invalid passcode");
    }
  }

  function handleLock() {
    setUnlocked(false);
    setPasscode("");
    setError(null);
  }

  async function handleDeleteAgent(agentId) {
    setError(null);
    setDeletingId(agentId);
    try {
      await deleteAgent(agentId, passcode.trim());
      setAgents((prev) => prev.filter((a) => a.id !== agentId));
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleDeleteSession(sessionId, agentId) {
    setError(null);
    setDeletingId(sessionId);
    try {
      await deleteSession(sessionId, agentId, passcode.trim());
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  const formatTime = (timeStr) => {
    try {
      const date = new Date(timeStr);
      return date.toLocaleString();
    } catch {
      return "Unknown";
    }
  };

  const backToApp = () => { window.location.href = "/"; };

  if (!unlocked) {
    return (
      <div className="flex flex-col h-full min-h-0 flex-1">
        <header className="shrink-0 px-4 py-4 border-b border-slate-700/50 bg-slate-900/50">
          <button
            type="button"
            onClick={backToApp}
            className="text-sm text-slate-400 hover:text-white mb-2 flex items-center gap-1"
          >
            ← Back to app
          </button>
          <h1 className="text-xl font-semibold text-white">Admin</h1>
          <p className="text-sm text-slate-400 mt-0.5">Enter passcode to manage agents and chats</p>
        </header>
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <form onSubmit={handleUnlock} className="max-w-xs space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Passcode</label>
              <input
                type="password"
                value={passcode}
                onChange={(e) => setPasscode(e.target.value)}
                placeholder="Admin passcode"
                className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                autoFocus
              />
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button
              type="submit"
              disabled={!passcode.trim()}
              className="w-full py-2.5 rounded-xl bg-amber-500 text-slate-900 font-medium hover:bg-amber-400 disabled:opacity-50"
            >
              Unlock
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 flex-1">
      <header className="shrink-0 px-4 py-4 border-b border-slate-700/50 bg-slate-900/50 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={backToApp}
          className="text-sm text-slate-400 hover:text-white flex items-center gap-1 shrink-0"
        >
          ← Back to app
        </button>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold text-white">Admin</h1>
          <div className="flex gap-2 mt-2">
            <button
              type="button"
              onClick={() => setActiveTab("agents")}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "agents"
                  ? "bg-amber-500 text-slate-900"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              Agents
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("chats")}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "chats"
                  ? "bg-amber-500 text-slate-900"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              Chats
            </button>
          </div>
        </div>
        <button
          type="button"
          onClick={handleLock}
          className="text-sm text-amber-400 hover:text-amber-300 shrink-0"
        >
          Lock
        </button>
      </header>
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {error && (
          <div className="mb-4 rounded-xl bg-red-900/20 border border-red-500/50 p-3 text-red-400 text-sm">
            {error}
          </div>
        )}
        {loading ? (
          <div className="flex justify-center py-8">
            <div className="flex gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        ) : activeTab === "agents" ? (
          agents.length === 0 ? (
            <p className="text-slate-400 text-sm">No agents to manage.</p>
          ) : (
            <ul className="space-y-3">
              {agents.map((agent) => (
                <li
                  key={agent.id}
                  className="flex items-center justify-between gap-3 rounded-xl bg-slate-800/70 border border-slate-600/50 p-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-white truncate">{agent.name}</p>
                    <p className="text-xs text-slate-500">{agent.model_id}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteAgent(agent.id)}
                    disabled={deletingId === agent.id}
                    className="shrink-0 px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 disabled:opacity-50 text-sm font-medium"
                  >
                    {deletingId === agent.id ? "Deleting…" : "Delete"}
                  </button>
                </li>
              ))}
            </ul>
          )
        ) : (
          sessions.length === 0 ? (
            <p className="text-slate-400 text-sm">No chat sessions to manage.</p>
          ) : (
            <ul className="space-y-3">
              {sessions.map((session) => (
                <li
                  key={session.session_id}
                  className="flex items-center justify-between gap-3 rounded-xl bg-slate-800/70 border border-slate-600/50 p-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-white truncate text-sm">
                      Session: {session.session_id.substring(0, 20)}...
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Agent: {session.agent_id || "Default"} • {session.message_count} messages
                    </p>
                    <p className="text-xs text-slate-600 mt-0.5">
                      Last: {formatTime(session.last_message_time)}
                    </p>
                    {session.preview && (
                      <p className="text-xs text-slate-500 mt-1 truncate">"{session.preview}"</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteSession(session.session_id, session.agent_id)}
                    disabled={deletingId === session.session_id}
                    className="shrink-0 px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 disabled:opacity-50 text-sm font-medium"
                  >
                    {deletingId === session.session_id ? "Deleting…" : "Delete"}
                  </button>
                </li>
              ))}
            </ul>
          )
        )}
      </div>
    </div>
  );
}
