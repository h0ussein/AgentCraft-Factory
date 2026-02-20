import { useState } from "react";
import BottomNav from "./components/BottomNav";
import ChatScreen from "./components/ChatScreen";
import ChatSelectorScreen from "./components/ChatSelectorScreen";
import MyAgentsScreen from "./components/MyAgentsScreen";
import CreationModal from "./components/CreationModal";
import CreateToolForm from "./components/CreateToolForm";
import CreateAgentForm from "./components/CreateAgentForm";
import AgentSelectionModal from "./components/AgentSelectionModal";
import AdminScreen from "./components/AdminScreen";

/** Admin is only at /admin (type in address bar). Not in the main nav. */
const isAdminRoute = () => window.location.pathname === "/admin";

/**
 * Mobile Web View – fixed width / centered container
 * Tabs: Chat (default), Add (+), My Agents. Admin: go to /admin in the URL.
 */
export default function App() {
  const [tab, setTab] = useState("chat");
  const [modalOpen, setModalOpen] = useState(false);
  const [toolFormOpen, setToolFormOpen] = useState(false);
  const [agentFormOpen, setAgentFormOpen] = useState(false);
  const [agentSelectionModalOpen, setAgentSelectionModalOpen] = useState(false);
  const [agentsVersion, setAgentsVersion] = useState(0);
  const [selectedAgent, setSelectedAgent] = useState(null); // { id, name } for chat
  const [currentSessionId, setCurrentSessionId] = useState(null); // null = show selector, string = show chat
  const [currentAgentId, setCurrentAgentId] = useState(null); // agent_id for current session

  const handleAdd = () => setModalOpen(true);
  const handleSelectAgent = (agent) => {
    setSelectedAgent(agent ? { id: agent.id, name: agent.name } : null);
    setTab("chat");
    setCurrentSessionId(null); // Show chat selector when agent is selected
  };

  const handleSelectChat = async (sessionId, agentId) => {
    setCurrentSessionId(sessionId);
    setCurrentAgentId(agentId);
    // If agent is different from selected, try to find it
    if (agentId && selectedAgent?.id !== agentId) {
      try {
        const { listAgents } = await import("./api");
        const agentsData = await listAgents();
        const agent = agentsData.agents?.find((a) => a.id === agentId);
        if (agent) {
          setSelectedAgent({ id: agent.id, name: agent.name });
        }
      } catch (err) {
        console.error("Failed to load agent info:", err);
      }
    }
  };

  const handleCreateNewChat = () => {
    // Check if an agent is selected
    if (!selectedAgent) {
      // Show agent selection modal
      setAgentSelectionModalOpen(true);
      return;
    }
    // Generate a new session ID to start a fresh chat
    const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setCurrentSessionId(newSessionId);
    setCurrentAgentId(selectedAgent.id);
  };

  const handleAgentSelectedFromModal = (agent) => {
    setSelectedAgent({ id: agent.id, name: agent.name });
    // Now create the chat with the selected agent
    const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setCurrentSessionId(newSessionId);
    setCurrentAgentId(agent.id);
  };

  const handleBackToChatSelector = () => {
    setCurrentSessionId(null);
  };
  const handleCreateTool = () => {
    setModalOpen(false);
    setToolFormOpen(true);
  };
  const handleCreateAgent = () => {
    setModalOpen(false);
    setAgentFormOpen(true);
  };
  const handleAgentCreated = (newAgentData) => {
    setAgentsVersion((v) => v + 1);
    // If agent was created from the selection modal, select it and create chat
    if (agentSelectionModalOpen || (newAgentData && newAgentData.id)) {
      if (newAgentData && newAgentData.id) {
        setSelectedAgent({ id: newAgentData.id, name: newAgentData.name });
        const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        setCurrentSessionId(newSessionId);
        setCurrentAgentId(newAgentData.id);
        setAgentSelectionModalOpen(false);
      }
    }
    setAgentFormOpen(false);
  };

  if (isAdminRoute()) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col w-full max-w-[var(--mobile-max-width,428px)] mx-auto min-w-0">
        <AdminScreen />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col w-full max-w-[var(--mobile-max-width,428px)] mx-auto min-w-0">
      <main className="flex-1 flex flex-col overflow-hidden pb-[calc(5rem+var(--safe-area-bottom,0px))]">
        {tab === "chat" && (
          currentSessionId === null ? (
            <ChatSelectorScreen
              onSelectChat={handleSelectChat}
              onCreateNewChat={handleCreateNewChat}
              selectedAgentId={selectedAgent?.id || null}
            />
          ) : (
            <ChatScreen
              sessionId={currentSessionId}
              selectedAgentId={currentAgentId || selectedAgent?.id || null}
              selectedAgentName={selectedAgent?.name}
              onBack={handleBackToChatSelector}
            />
          )
        )}
        {tab === "agents" && (
          <MyAgentsScreen
            key={agentsVersion}
            onSelectAgent={handleSelectAgent}
          />
        )}
      </main>

      <BottomNav
        active={tab}
        onChat={() => {
          setTab("chat");
          // If in chat tab, show selector if no session selected
          if (currentSessionId === null) {
            // Already showing selector
          } else {
            // Could optionally go back to selector, or keep current chat
          }
        }}
        onAdd={handleAdd}
        onMyAgents={() => setTab("agents")}
      />

      {modalOpen && (
        <CreationModal
          onClose={() => setModalOpen(false)}
          onCreateAgent={handleCreateAgent}
          onCreateTool={handleCreateTool}
        />
      )}

      {toolFormOpen && (
        <CreateToolForm
          onClose={() => setToolFormOpen(false)}
          onSuccess={() => setToolFormOpen(false)}
        />
      )}

      {agentFormOpen && (
        <CreateAgentForm
          onClose={() => {
            setAgentFormOpen(false);
            setAgentSelectionModalOpen(false);
          }}
          onSuccess={handleAgentCreated}
        />
      )}

      {agentSelectionModalOpen && (
        <AgentSelectionModal
          onSelectAgent={handleAgentSelectedFromModal}
          onCreateAgent={() => {
            setAgentSelectionModalOpen(false);
            setAgentFormOpen(true);
          }}
          onClose={() => setAgentSelectionModalOpen(false)}
        />
      )}
    </div>
  );
}
