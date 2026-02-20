/**
 * API client for Dynamic AI Agent Factory backend
 * In production the same server serves frontend + API, so use relative URL.
 */
const API_BASE = import.meta.env.PROD ? "" : "http://localhost:8000";

export async function sendChat(message, sessionId = null, agentId = null) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      ...(sessionId && { session_id: sessionId }),
      ...(agentId && { agent_id: agentId }),
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Chat failed: ${res.status}`);
  }
  return res.json();
}

export async function createTool(prompt, toolName = null, agentId = null) {
  const res = await fetch(`${API_BASE}/create-tool`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      ...(toolName && { tool_name: toolName }),
      ...(agentId && { agent_id: agentId }),
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Create tool failed: ${res.status}`);
  }
  return res.json();
}

export async function listAgents() {
  const res = await fetch(`${API_BASE}/agents`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to list agents");
  }
  return res.json();
}

export async function createAgent(name, systemInstruction = "", modelId = "gemini-2.5-flash") {
  const res = await fetch(`${API_BASE}/agents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: name.trim(),
      system_instruction: systemInstruction.trim(),
      model_id: modelId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create agent");
  }
  return res.json();
}

export async function listTools() {
  const res = await fetch(`${API_BASE}/tools`);
  if (!res.ok) throw new Error("Failed to list tools");
  return res.json();
}

/** Verify admin passcode (unlock Admin UI). */
export async function verifyAdminPasscode(passcode) {
  const res = await fetch(`${API_BASE}/admin/verify`, {
    headers: { "X-Admin-Passcode": passcode },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Invalid passcode");
  }
  return res.json();
}

/** Delete an agent. Requires admin passcode in header. */
export async function deleteAgent(agentId, passcode) {
  const res = await fetch(`${API_BASE}/agents/${agentId}`, {
    method: "DELETE",
    headers: { "X-Admin-Passcode": passcode },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to delete agent");
  }
  return res.json();
}
