/**
 * API client for Dynamic AI Agent Factory backend
 * Same server serves frontend + API at /api (so SPA routes like /agents work).
 */
const API_BASE = import.meta.env.PROD ? "/api" : "http://localhost:8000/api";

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
    // Handle 429 (rate limit/quota exceeded) with friendly message
    if (res.status === 429) {
      throw new Error(err.detail || "The AI service is currently at capacity. Please try again in a few moments.");
    }
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
    // Handle 429 (rate limit/quota exceeded) with friendly message
    if (res.status === 429) {
      throw new Error(err.detail || "The AI service is currently at capacity. Please try again in a few moments.");
    }
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
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to list tools");
  }
  return res.json();
}

export async function listSessions(agentId = null) {
  const url = agentId ? `${API_BASE}/sessions?agent_id=${agentId}` : `${API_BASE}/sessions`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to list sessions");
  }
  return res.json();
}

export async function getChatHistory(sessionId, agentId = null) {
  const url = agentId ? `${API_BASE}/sessions/${sessionId}/history?agent_id=${agentId}` : `${API_BASE}/sessions/${sessionId}/history`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to get chat history");
  }
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

/** Delete a chat session. Requires admin passcode in header. */
export async function deleteSession(sessionId, agentId = null, passcode) {
  const url = agentId ? `${API_BASE}/sessions/${sessionId}?agent_id=${agentId}` : `${API_BASE}/sessions/${sessionId}`;
  const res = await fetch(url, {
    method: "DELETE",
    headers: { "X-Admin-Passcode": passcode },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to delete session");
  }
  return res.json();
}

/** List admin-defined APIs (for tool creation). Requires passcode. */
export async function listAdminApis(passcode) {
  const res = await fetch(`${API_BASE}/admin/apis`, {
    headers: { "X-Admin-Passcode": passcode },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to list APIs");
  }
  return res.json();
}

/** Create or update an admin API (description, key_name, key_value). Requires passcode. */
export async function createAdminApi(passcode, description, keyName, keyValue) {
  const res = await fetch(`${API_BASE}/admin/apis`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Passcode": passcode,
    },
    body: JSON.stringify({
      description: description.trim(),
      key_name: keyName.trim(),
      key_value: keyValue.trim(),
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create API");
  }
  return res.json();
}
