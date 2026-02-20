/**
 * Chat Screen – messages from /chat, loading spinner when agent is thinking
 * User messages: neon purple right; Agent messages: dark grey left
 */

import { useState, useRef, useEffect } from "react";
import { sendChat } from "../api";

const SESSION_ID = "mobile-session-1";

export default function ChatScreen({ selectedAgentId = null, selectedAgentName = null }) {
  const [messages, setMessages] = useState([
    {
      role: "agent",
      content: "Hello! I am online and ready to assist you. You can ask me to use tools or answer questions. How can I help you today?",
      id: "welcome",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text, id: `u-${Date.now()}` }]);
    setLoading(true);
    try {
      const data = await sendChat(text, SESSION_ID, selectedAgentId || undefined);
      const reply = data?.response ?? "No response.";
      setMessages((prev) => [...prev, { role: "agent", content: reply, id: `a-${Date.now()}` }]);
    } catch (err) {
      setError(err.message || "Something went wrong");
      setMessages((prev) => [
        ...prev,
        { role: "agent", content: `Error: ${err.message}`, id: `err-${Date.now()}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const today = new Date();
  const timeStr = today.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });

  return (
    <div className="flex flex-col h-full min-h-0 flex-1">
      {/* Header */}
      <header className="flex items-center justify-between px-3 sm:px-4 py-3 border-b border-slate-700/50 bg-slate-900/50 shrink-0 gap-2">
        <button className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center -ml-1 text-slate-400 hover:text-white touch-manipulation" aria-label="Back">
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-purple-500/30 flex items-center justify-center">
            <svg className="w-5 h-5 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="10" rx="2" />
              <circle cx="12" cy="5" r="2" />
            </svg>
          </div>
          <div>
            <p className="font-medium text-white text-sm">{selectedAgentName || "Assistant Agent"}</p>
            <p className="text-xs text-green-500">Online</p>
          </div>
        </div>
        <button className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center -mr-1 text-slate-400 hover:text-white touch-manipulation" aria-label="Menu">
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="5" r="1.5" />
            <circle cx="12" cy="12" r="1.5" />
            <circle cx="12" cy="19" r="1.5" />
          </svg>
        </button>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 sm:px-4 py-4 space-y-4">
        <p className="text-center text-xs text-slate-500">Today, {timeStr}</p>

        {messages.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className="flex justify-end gap-2">
              <div className="max-w-[85%] min-w-0 rounded-2xl rounded-br-md bg-purple-500/90 text-white px-4 py-2.5 text-sm break-words">
                {m.content}
              </div>
              <div className="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center shrink-0">
                <svg className="w-4 h-4 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </div>
            </div>
          ) : (
            <div key={m.id} className="flex justify-start gap-2">
              <div className="w-8 h-8 rounded-full bg-purple-500/30 flex items-center justify-center shrink-0">
                <svg className="w-4 h-4 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="10" rx="2" />
                  <circle cx="12" cy="5" r="2" />
                </svg>
              </div>
              <div className="max-w-[85%] min-w-0 rounded-2xl rounded-bl-md bg-slate-700/80 text-slate-100 px-4 py-2.5 text-sm break-words">
                {m.content}
              </div>
            </div>
          )
        )}

        {loading && (
          <div className="flex justify-start gap-2">
            <div className="w-8 h-8 rounded-full bg-purple-500/30 flex items-center justify-center shrink-0">
              <svg className="w-4 h-4 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="10" rx="2" />
                <circle cx="12" cy="5" r="2" />
              </svg>
            </div>
            <div className="rounded-2xl rounded-bl-md bg-slate-700/80 px-4 py-3 flex gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-1 sm:gap-2 px-3 sm:px-4 py-3 border-t border-slate-700/50 bg-slate-900/30 shrink-0"
        style={{ paddingBottom: "calc(0.75rem + var(--safe-area-bottom, 0px))" }}
      >
        <button
          type="button"
          className="w-10 h-10 min-w-[40px] min-h-[40px] rounded-full bg-slate-700/80 flex items-center justify-center text-slate-400 hover:text-white shrink-0 touch-manipulation"
          aria-label="Attach"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message..."
          className="flex-1 min-w-0 px-3 sm:px-4 py-2.5 rounded-full bg-slate-800/80 border border-slate-600 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-transparent text-base"
          disabled={loading}
        />
        <button
          type="button"
          className="w-10 h-10 min-w-[40px] min-h-[40px] flex items-center justify-center text-slate-400 hover:text-white shrink-0 touch-manipulation"
          aria-label="Voice"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" />
          </svg>
        </button>
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="w-10 h-10 min-w-[40px] min-h-[40px] rounded-full bg-purple-500 flex items-center justify-center text-white hover:bg-purple-400 disabled:opacity-50 shrink-0 touch-manipulation"
          aria-label="Send"
        >
          <svg className="w-5 h-5 ml-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </div>
  );
}
