/**
 * Create Agent Form – name, model (2.5 Flash / 2.5 Pro / 3 Flash), optional system instruction
 */

import { useState } from "react";
import { createAgent } from "../api";

const MODEL_OPTIONS = [
  { id: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
  { id: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
  { id: "gemini-3-flash-preview", label: "Gemini 3 Flash" },
];

export default function CreateAgentForm({ onClose, onSuccess }) {
  const [name, setName] = useState("");
  const [modelId, setModelId] = useState("gemini-2.5-flash");
  const [systemInstruction, setSystemInstruction] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    setLoading(true);
    try {
      const data = await createAgent(name.trim(), systemInstruction.trim(), modelId);
      setResult(data);
      onSuccess?.(data);
    } catch (err) {
      setError(err.message || "Failed to create agent");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-2xl bg-slate-800/95 border border-slate-600/50 shadow-xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Create New Agent</h2>
          <button
            type="button"
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

        {result ? (
          <div className="py-4">
            <p className="text-sm text-green-400 font-medium">Agent created successfully</p>
            <p className="text-slate-300 mt-1">{result.name}</p>
            <button
              type="button"
              onClick={onClose}
              className="mt-4 w-full py-2 rounded-xl bg-purple-500 text-white font-medium hover:bg-purple-400 transition-colors"
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Research Assistant"
                className="w-full px-4 py-2.5 rounded-xl bg-slate-700/80 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Model</label>
              <select
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-700/80 border border-slate-600 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                {MODEL_OPTIONS.map((m) => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">System instruction (optional)</label>
              <textarea
                value={systemInstruction}
                onChange={(e) => setSystemInstruction(e.target.value)}
                placeholder="How this agent should behave..."
                rows={3}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-700/80 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
              />
            </div>
            {error && (
              <p className="text-sm text-red-400">{error}</p>
            )}
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2.5 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !name.trim()}
                className="flex-1 py-2.5 rounded-xl bg-purple-500 text-white font-medium hover:bg-purple-400 disabled:opacity-50 transition-colors"
              >
                {loading ? "Creating…" : "Create"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
