/**
 * Chat Selector Screen – Shows list of existing chats and option to create new
 * Displayed when app first loads or when user wants to switch chats
 */

import { useState, useEffect } from "react";
import { listSessions, listAgents } from "../api";

export default function ChatSelectorScreen({ onSelectChat, onCreateNewChat, selectedAgentId = null }) {
  const [sessions, setSessions] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        const [sessionsData, agentsData] = await Promise.all([
          listSessions(selectedAgentId),
          listAgents(),
        ]);
        setSessions(sessionsData.sessions || []);
        setAgents(agentsData.agents || []);
      } catch (err) {
        setError(err.message || "Failed to load chats");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [selectedAgentId]);

  const getAgentName = (agentId) => {
    const agent = agents.find((a) => a.id === agentId);
    return agent ? agent.name : "Unknown Agent";
  };

  const formatTime = (timeStr) => {
    try {
      const date = new Date(timeStr);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return "Just now";
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
      return date.toLocaleDateString();
    } catch {
      return "Recently";
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0 flex-1 bg-slate-950">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-4 border-b border-slate-700/50 bg-slate-900/50 shrink-0">
        <h1 className="text-xl font-semibold text-white">Chats</h1>
        <button
          onClick={onCreateNewChat}
          className="px-4 py-2 rounded-full bg-purple-500 hover:bg-purple-400 text-white text-sm font-medium transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Chat
        </button>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="flex gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}

        {error && (
          <div className="py-8">
            <p className="text-sm text-red-400 text-center">{error}</p>
          </div>
        )}

        {!loading && !error && sessions.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 px-4">
            <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <p className="text-slate-400 text-center mb-6">No chats yet</p>
            <button
              onClick={onCreateNewChat}
              className="px-6 py-3 rounded-full bg-purple-500 hover:bg-purple-400 text-white font-medium transition-colors"
            >
              Start New Chat
            </button>
          </div>
        )}

        {!loading && !error && sessions.length > 0 && (
          <div className="space-y-2">
            {sessions.map((session) => (
              <button
                key={session.session_id}
                onClick={() => onSelectChat(session.session_id, session.agent_id)}
                className="w-full text-left px-4 py-3 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 hover:border-purple-500/50 transition-colors group"
              >
                <div className="flex items-start gap-3">
                  <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center shrink-0 group-hover:bg-purple-500/30 transition-colors">
                    <svg className="w-6 h-6 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-white font-medium text-sm truncate">
                        {getAgentName(session.agent_id)}
                      </p>
                      <span className="text-xs text-slate-500 shrink-0 ml-2">
                        {formatTime(session.last_message_time)}
                      </span>
                    </div>
                    {session.preview && (
                      <p className="text-slate-400 text-xs truncate">{session.preview}</p>
                    )}
                    {session.message_count > 0 && (
                      <p className="text-slate-500 text-xs mt-1">{session.message_count} messages</p>
                    )}
                  </div>
                  <svg className="w-5 h-5 text-slate-400 group-hover:text-purple-400 transition-colors shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 18l6-6-6-6" />
                  </svg>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
