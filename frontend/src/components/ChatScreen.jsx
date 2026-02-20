/**
 * Chat Screen – messages from /chat, loading spinner when agent is thinking
 * User messages: neon purple right; Agent messages: dark grey left
 */

import { useState, useRef, useEffect } from "react";
import { sendChat, getChatHistory } from "../api";
import ToolSelectorModal from "./ToolSelectorModal";

function generateSessionId() {
  return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export default function ChatScreen({ 
  sessionId: propSessionId = null, 
  selectedAgentId = null, 
  selectedAgentName = null,
  onBack = null 
}) {
  const [sessionId, setSessionId] = useState(propSessionId || generateSessionId());
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(!!propSessionId);
  const [error, setError] = useState(null);
  const [toolSelectorOpen, setToolSelectorOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null); // { name, path }
  const bottomRef = useRef(null);

  // Update sessionId when propSessionId changes
  useEffect(() => {
    if (propSessionId) {
      setSessionId(propSessionId);
    } else if (!propSessionId && !sessionId) {
      setSessionId(generateSessionId());
    }
  }, [propSessionId]);

  // Load chat history when sessionId is provided
  useEffect(() => {
    if (propSessionId) {
      async function loadHistory() {
        try {
          setLoadingHistory(true);
          const history = await getChatHistory(propSessionId, selectedAgentId || undefined);
          if (history.messages && history.messages.length > 0) {
            // Convert backend messages to frontend format
            const formattedMessages = history.messages.map((msg, idx) => ({
              role: msg.role,
              content: msg.content,
              id: `${msg.role}-${idx}-${msg.timestamp || Date.now()}`,
            }));
            setMessages(formattedMessages);
          } else {
            // No history, show welcome message
            setMessages([
              {
                role: "agent",
                content: "Hello! I am online and ready to assist you. You can ask me to use tools or answer questions. How can I help you today?",
                id: "welcome",
              },
            ]);
          }
        } catch (err) {
          console.error("Failed to load chat history:", err);
          // Show welcome message on error
          setMessages([
            {
              role: "agent",
              content: "Hello! I am online and ready to assist you. You can ask me to use tools or answer questions. How can I help you today?",
              id: "welcome",
            },
          ]);
        } finally {
          setLoadingHistory(false);
        }
      }
      loadHistory();
    } else {
      // New chat, show welcome message
      setMessages([
        {
          role: "agent",
          content: "Hello! I am online and ready to assist you. You can ask me to use tools or answer questions. How can I help you today?",
          id: "welcome",
        },
      ]);
    }
  }, [propSessionId, selectedAgentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    
    // Build message with tool reference if tool is selected
    let messageToSend = text;
    if (selectedTool) {
      messageToSend = `Use tool: ${selectedTool.name}\n\n${text}`;
    }
    
    setInput("");
    setError(null);
    setSelectedTool(null); // Clear selected tool after sending
    setMessages((prev) => [...prev, { role: "user", content: text, id: `u-${Date.now()}` }]);
    setLoading(true);
    try {
      const data = await sendChat(messageToSend, sessionId, selectedAgentId || undefined);
      const reply = data?.response ?? "No response.";
      // Update sessionId if backend returned a different one
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
      }
      setMessages((prev) => [...prev, { role: "agent", content: reply, id: `a-${Date.now()}` }]);
    } catch (err) {
      const errorMessage = err.message || "Something went wrong";
      setError(errorMessage);
      // Show user-friendly error message in chat
      const friendlyMessage = errorMessage.includes("capacity") || errorMessage.includes("quota") 
        ? "⚠️ The AI service is currently at capacity. This usually means the API quota has been exceeded. Please try again in a few moments, or contact support if the issue persists."
        : `Error: ${errorMessage}`;
      setMessages((prev) => [
        ...prev,
        { role: "agent", content: friendlyMessage, id: `err-${Date.now()}` },
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
        <button 
          onClick={onBack || undefined}
          className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center -ml-1 text-slate-400 hover:text-white touch-manipulation" 
          aria-label="Back"
        >
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
        {loadingHistory ? (
          <div className="flex items-center justify-center py-12">
            <div className="flex gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        ) : (
          <>
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
                  <div className={`max-w-[85%] min-w-0 rounded-2xl rounded-bl-md px-4 py-2.5 text-sm break-words ${
                    m.content.includes("⚠️") || m.content.includes("capacity") || m.content.includes("quota")
                      ? "bg-yellow-500/20 border border-yellow-500/50 text-yellow-100"
                      : "bg-slate-700/80 text-slate-100"
                  }`}>
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
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex flex-col border-t border-slate-700/50 bg-slate-900/30 shrink-0"
        style={{ paddingBottom: "calc(0.75rem + var(--safe-area-bottom, 0px))" }}
      >
        {/* Selected Tool Badge */}
        {selectedTool && (
          <div className="px-3 sm:px-4 pt-2 pb-1">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-purple-500/20 border border-purple-500/50">
              <div className="w-6 h-6 rounded bg-purple-500/30 flex items-center justify-center shrink-0">
                <svg className="w-4 h-4 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                </svg>
              </div>
              <span className="flex-1 text-sm text-purple-200 font-medium truncate">{selectedTool.name}</span>
              <button
                type="button"
                onClick={() => setSelectedTool(null)}
                className="w-5 h-5 rounded-full hover:bg-purple-500/30 flex items-center justify-center text-purple-300 hover:text-white transition-colors shrink-0"
                aria-label="Remove tool"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>
        )}
        
        <div className="flex items-center gap-1 sm:gap-2 px-3 sm:px-4">
          <button
            type="button"
            onClick={() => setToolSelectorOpen(true)}
            className={`w-10 h-10 min-w-[40px] min-h-[40px] rounded-full flex items-center justify-center shrink-0 touch-manipulation transition-colors ${
              selectedTool 
                ? "bg-purple-500/30 text-purple-400 hover:bg-purple-500/40" 
                : "bg-slate-700/80 text-slate-400 hover:text-white"
            }`}
            aria-label="Select Tool"
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
        </div>
      </form>

      {toolSelectorOpen && (
        <ToolSelectorModal
          onClose={() => setToolSelectorOpen(false)}
          onSelectTool={(tool) => {
            // Set selected tool instead of inserting text
            setSelectedTool({ name: tool.name, path: tool.path });
            setToolSelectorOpen(false);
          }}
        />
      )}
    </div>
  );
}
