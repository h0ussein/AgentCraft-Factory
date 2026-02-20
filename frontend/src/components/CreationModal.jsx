/**
 * Creation Modal – "Create New Agent" and "Create New Tool"
 * Shown when the Add (+) button is clicked
 */

export default function CreationModal({ onClose, onCreateAgent, onCreateTool }) {
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
          <h2 className="text-lg font-semibold text-white">Initialize New Instance</h2>
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
        <p className="text-sm text-slate-400 mb-6">
          Select the type of AI component you wish to deploy to your workspace.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          <button
            onClick={() => { onClose(); onCreateAgent?.(); }}
            className="flex flex-col items-center p-4 rounded-xl border-2 border-purple-500/60 bg-slate-800 hover:bg-slate-700/80 hover:border-purple-400 transition-colors text-left"
          >
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-purple-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="10" rx="2" />
                <circle cx="12" cy="5" r="2" />
                <path d="M12 7v4" />
              </svg>
            </div>
            <span className="font-medium text-white text-sm">Create New Agent</span>
            <span className="text-xs text-slate-400 mt-1 leading-tight">
              Deploy an autonomous AI assistant with specific goals, memory, and persona.
            </span>
          </button>

          <button
            onClick={() => { onClose(); onCreateTool?.(); }}
            className="flex flex-col items-center p-4 rounded-xl border-2 border-cyan-500/60 bg-slate-800 hover:bg-slate-700/80 hover:border-cyan-400 transition-colors text-left"
          >
            <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
              </svg>
            </div>
            <span className="font-medium text-white text-sm">Create New Tool</span>
            <span className="text-xs text-slate-400 mt-1 leading-tight">
              Configure a utility function, API connector, or scraper for your agents.
            </span>
          </button>
        </div>

        <p className="flex items-center gap-2 mt-5 text-xs text-slate-500">
          <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4M12 8h.01" />
          </svg>
          Pro tip: You can also use "/" commands in chat to quick-create.
        </p>
      </div>
    </div>
  );
}
