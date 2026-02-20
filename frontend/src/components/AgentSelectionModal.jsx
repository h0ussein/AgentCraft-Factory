/**
 * Agent Selection Modal – Shows when user tries to create a new chat without selecting an agent
 * Allows user to select an existing agent or create a new one
 */

import { useState, useEffect } from "react";
import { listAgents } from "../api";

export default function AgentSelectionModal({ 
  onSelectAgent, 
  onCreateAgent, 
  onClose 
}) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchAgents() {
      try {
        setLoading(true);
        setError(null);
        const data = await listAgents();
        setAgents(data.agents || []);
      } catch (err) {
        setError(err.message || "Failed to load agents");
      } finally {
        setLoading(false);
      }
    }
    fetchAgents();
  }, []);

  const handleAgentSelect = (agent) => {
    onSelectAgent(agent);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/60 backdrop-blur-sm"
      style={{ paddingBottom: "var(--safe-area-bottom, 0px)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-t-2xl sm:rounded-2xl bg-slate-800/95 border border-slate-600/50 shadow-xl shadow-black/20 p-6 pb-[calc(1.5rem+var(--safe-area-bottom,0px))] max-h-[90vh] overflow-y-auto mx-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Select an Agent</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <p className="text-sm text-slate-400 mb-4">
          You need to select an agent before starting a new chat.
        </p>

        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="flex gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}

        {error && (
          <div className="py-4">
            <p className="text-sm text-red-400 text-center">{error}</p>
          </div>
        )}

        {!loading && !error && (
          <>
            {agents.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-sm text-slate-400 mb-4">No agents available.</p>
                <button
                  onClick={() => {
                    onClose();
                    onCreateAgent();
                  }}
                  className="px-6 py-3 rounded-full bg-purple-500 hover:bg-purple-400 text-white font-medium transition-colors"
                >
                  Create New Agent
                </button>
              </div>
            ) : (
              <>
                <div className="space-y-2 mb-4">
                  {agents.map((agent) => (
                    <button
                      key={agent.id}
                      onClick={() => handleAgentSelect(agent)}
                      className="w-full text-left px-4 py-3 rounded-xl bg-slate-700/50 hover:bg-slate-700 border border-slate-600/50 hover:border-purple-500/50 transition-colors group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center shrink-0 group-hover:bg-purple-500/30 transition-colors">
                          <svg className="w-5 h-5 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="11" width="18" height="10" rx="2" />
                            <circle cx="12" cy="5" r="2" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-white font-medium text-sm truncate">{agent.name}</p>
                          <p className="text-slate-400 text-xs truncate mt-0.5">{agent.model_id}</p>
                        </div>
                        <svg className="w-5 h-5 text-slate-400 group-hover:text-purple-400 transition-colors shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M9 18l6-6-6-6" />
                        </svg>
                      </div>
                    </button>
                  ))}
                </div>

                <div className="pt-4 border-t border-slate-700/50">
                  <button
                    onClick={() => {
                      onClose();
                      onCreateAgent();
                    }}
                    className="w-full px-4 py-3 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/50 text-purple-300 hover:text-purple-200 font-medium transition-colors flex items-center justify-center gap-2"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    Create New Agent
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
