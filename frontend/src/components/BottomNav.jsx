/**
 * Bottom Navigation Bar – Chat, Add (+), My Agents
 * Admin is only via URL: /admin
 */

export default function BottomNav({ active, onChat, onAdd, onMyAgents }) {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around py-2 px-1 sm:px-2 bg-slate-900/70 backdrop-blur-md border-t border-slate-700/50 max-w-[var(--mobile-max-width,428px)] mx-auto"
      style={{ paddingBottom: "calc(0.5rem + var(--safe-area-bottom, 0px))" }}
    >
      <button
        onClick={onChat}
        className="flex flex-col items-center gap-0.5 text-xs transition-colors min-h-[44px] min-w-[36px] justify-center touch-manipulation"
      >
        <svg
          className={`w-6 h-6 flex-shrink-0 ${active === "chat" ? "text-purple-500 fill-current" : "text-slate-400"}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        <span className={active === "chat" ? "text-purple-500" : "text-slate-400"}>Chat</span>
      </button>

      <button
        onClick={onAdd}
        className="flex items-center justify-center w-12 h-12 min-w-[48px] min-h-[48px] rounded-full bg-purple-500 text-white shadow-lg shadow-purple-500/30 hover:bg-purple-400 active:scale-95 transition-colors touch-manipulation"
        aria-label="Add"
      >
        <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>

      <button
        onClick={onMyAgents}
        className="flex flex-col items-center gap-0.5 text-xs transition-colors min-h-[44px] min-w-[36px] justify-center touch-manipulation"
      >
        <svg
          className={`w-6 h-6 ${active === "agents" ? "text-purple-500" : "text-slate-400"}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
        <span className={active === "agents" ? "text-purple-500" : "text-slate-400"}>Agents</span>
      </button>
    </nav>
  );
}
