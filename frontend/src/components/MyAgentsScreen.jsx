/**
 * My Agents View – lists all agents from the database
 * Each card shows agent name and the tools attached to it.
 * Glassmorphism + dark neon theme.
 */

import { useState, useEffect } from "react";
import { listAgents } from "../api";

export default function MyAgentsScreen({ onSelectAgent }) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    listAgents()
      .then((data) => {
        if (!cancelled) setAgents(data.agents || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Failed to load agents");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="flex flex-col h-full min-h-0 flex-1">
      <header className="shrink-0 px-3 sm:px-4 py-4 border-b border-slate-700/50 bg-slate-900/50">
        <h1 className="text-lg sm:text-xl font-semibold text-white">My Agents</h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-0.5">Agents and their tools from the database</p>
      </header>

      <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 sm:px-4 py-4">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="flex gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-500 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 rounded-full bg-purple-500 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 rounded-full bg-purple-500 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-xl bg-slate-800/80 border border-slate-600 p-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {!loading && !error && agents.length === 0 && (
          <div className="rounded-xl bg-slate-800/50 border border-slate-700 p-6 text-center text-slate-400 text-sm">
            No agents yet. Use the + button to create one.
          </div>
        )}

        {!loading && !error && agents.length > 0 && (
          <ul className="space-y-4">
            {agents.map((agent) => (
              <li key={agent.id}>
                <button
                  type="button"
                  onClick={() => onSelectAgent?.(agent)}
                  className="w-full text-left rounded-2xl bg-slate-800/70 backdrop-blur-sm border border-slate-600/50 shadow-lg overflow-hidden hover:bg-slate-700/70 hover:border-purple-500/40 transition-colors active:scale-[0.99]"
                >
                  <div className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center shrink-0">
                        <svg className="w-5 h-5 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="3" y="11" width="18" height="10" rx="2" />
                          <circle cx="12" cy="5" r="2" />
                        </svg>
                      </div>
                      <div className="min-w-0 flex-1">
                        <h2 className="font-semibold text-white truncate">{agent.name}</h2>
                        <p className="text-xs text-slate-500 mt-0.5">{agent.model_id}</p>
                      </div>
                      <span className="text-xs text-purple-400 font-medium shrink-0">Chat →</span>
                    </div>
                    <div className="mt-3">
                      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Tools attached</p>
                      {agent.tools && agent.tools.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {agent.tools.map((t) => (
                            <span
                              key={t.id}
                              className="inline-flex items-center px-2.5 py-1 rounded-lg bg-slate-700/80 text-slate-300 text-xs border border-slate-600/50"
                            >
                              {t.name}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500">No tools assigned</p>
                      )}
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
