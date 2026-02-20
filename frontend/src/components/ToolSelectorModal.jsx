/**
 * Tool Selector Modal – Shows available tools for selection
 * Displayed when the plus icon in chat input is clicked
 */

import { useState, useEffect } from "react";
import { listTools } from "../api";

export default function ToolSelectorModal({ onClose, onSelectTool }) {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchTools() {
      try {
        setLoading(true);
        setError(null);
        const data = await listTools();
        setTools(data.files || []);
      } catch (err) {
        setError(err.message || "Failed to load tools");
      } finally {
        setLoading(false);
      }
    }
    fetchTools();
  }, []);

  const handleToolSelect = (tool) => {
    onSelectTool(tool);
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
          <h2 className="text-lg font-semibold text-white">Select a Tool</h2>
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

        {!loading && !error && tools.length === 0 && (
          <div className="py-8">
            <p className="text-sm text-slate-400 text-center">No tools available. Create a tool first.</p>
          </div>
        )}

        {!loading && !error && tools.length > 0 && (
          <div className="space-y-2">
            {tools.map((tool, index) => (
              <button
                key={index}
                onClick={() => handleToolSelect(tool)}
                className="w-full text-left px-4 py-3 rounded-xl bg-slate-700/50 hover:bg-slate-700 border border-slate-600/50 hover:border-purple-500/50 transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center shrink-0 group-hover:bg-purple-500/30 transition-colors">
                    <svg className="w-5 h-5 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium text-sm truncate">{tool.name}</p>
                    <p className="text-slate-400 text-xs truncate mt-0.5">{tool.path}</p>
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
