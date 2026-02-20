import { useState } from "react";
import BottomNav from "./components/BottomNav";
import ChatScreen from "./components/ChatScreen";
import MyAgentsScreen from "./components/MyAgentsScreen";
import CreationModal from "./components/CreationModal";
import CreateToolForm from "./components/CreateToolForm";
import CreateAgentForm from "./components/CreateAgentForm";
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
  const [agentsVersion, setAgentsVersion] = useState(0);
  const [selectedAgent, setSelectedAgent] = useState(null); // { id, name } for chat

  const handleAdd = () => setModalOpen(true);
  const handleSelectAgent = (agent) => {
    setSelectedAgent(agent ? { id: agent.id, name: agent.name } : null);
    setTab("chat");
  };
  const handleCreateTool = () => {
    setModalOpen(false);
    setToolFormOpen(true);
  };
  const handleCreateAgent = () => {
    setModalOpen(false);
    setAgentFormOpen(true);
  };
  const handleAgentCreated = () => {
    setAgentFormOpen(false);
    setAgentsVersion((v) => v + 1);
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
          <ChatScreen
            selectedAgentId={selectedAgent?.id}
            selectedAgentName={selectedAgent?.name}
          />
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
        onChat={() => setTab("chat")}
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
          onClose={() => setAgentFormOpen(false)}
          onSuccess={handleAgentCreated}
        />
      )}
    </div>
  );
}
