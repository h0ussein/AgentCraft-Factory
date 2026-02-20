/**
 * Create Tool Form – text area + agent dropdown, POSTs to /create-tool
 * Assign the new tool to the selected agent.
 */

import { useState, useEffect } from "react";
import { createTool, listAgents } from "../api";

const PLACEHOLDER =
  "e.g., Create a tool that fetches the current price of Bitcoin in USD and returns a summary for an investor. Use the CoinGecko public API.";

export default function CreateToolForm({ onClose, onSuccess }) {
  const [prompt, setPrompt] = useState("");
  const [agentId, setAgentId] = useState("");
  const [agents, setAgents] = useState([]);
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    let cancelled = false;
    listAgents()
      .then((data) => {
        if (!cancelled) {
          setAgents(data.agents || []);
          if (data.agents?.length > 0 && !agentId) setAgentId(data.agents[0].id);
        }
      })
      .catch(() => {
        if (!cancelled) setAgents([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingAgents(false);
      });
    return () => { cancelled = true; };
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setError(null);
    setLoading(true);
    try {
      const data = await createTool(prompt.trim(), null, agentId || null);
      setResult(data);
      onSuccess?.(data);
    } catch (err) {
      setError(err.message || "Failed to create tool");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-sm overflow-y-auto"
      style={{ paddingBottom: "calc(1rem + var(--safe-area-bottom, 0px))" }}
    >
      <div
        className="w-full max-w-md rounded-t-2xl sm:rounded-2xl bg-slate-800/95 border border-slate-600/50 shadow-xl shadow-black/20 backdrop-blur-sm p-6 pb-[calc(1.5rem+var(--safe-area-bottom,0px))] max-h-[90vh] overflow-y-auto my-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Create New Tool</h2>
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

        <p className="text-sm text-slate-400 mb-3">What should this tool do?</p>
        <form onSubmit={handleSubmit}>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={PLACEHOLDER}
            rows={5}
            className="w-full px-4 py-3 rounded-xl bg-slate-900/80 border border-slate-600 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 resize-none"
            disabled={loading}
          />

          <div className="mt-4">
            <label className="block text-sm font-medium text-slate-400 mb-2">Assign to agent</label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900/80 border border-slate-600 text-slate-100 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50"
              disabled={loadingAgents || loading}
            >
              {loadingAgents && <option value="">Loading agents…</option>}
              {!loadingAgents && agents.length === 0 && <option value="">No agents in database</option>}
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <p className="mt-2 text-sm text-red-400">{error}</p>
          )}
          {result && (
            <div className="mt-3 p-3 rounded-lg bg-slate-900 border border-slate-600">
              <p className="text-sm text-green-400 font-medium">Tool created successfully</p>
              <p className="text-xs text-slate-400 mt-1">{result.file_name}</p>
            </div>
          )}
          <div className="flex gap-3 mt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 min-h-[44px] py-2.5 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-700 transition-colors touch-manipulation"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              className="flex-1 min-h-[44px] py-2.5 rounded-xl bg-purple-500 text-white font-medium hover:bg-purple-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors touch-manipulation"
            >
              {loading ? "Creating…" : "Create Tool"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
