import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import CharactersPage from "./pages/CharactersPage";
import CampaignsPage from "./pages/CampaignsPage";
import AdventuresPage from "./pages/AdventuresPage";
import PlayPage from "./pages/PlayPage";
import SettingsPage from "./pages/SettingsPage";
import { api } from "./api/client";

const queryClient = new QueryClient();

function HomeWrapper() {
  const [indexed, setIndexed] = useState(false);
  const [claudeOk, setClaudeOk] = useState(false);
  const [recent, setRecent] = useState<{ id: string; name: string } | null>(null);

  useEffect(() => {
    api.health().then((h) => {
      setIndexed(h.indexed);
      setClaudeOk(h.claude_configured);
    });
    api.listSessions().then((s) => {
      if (s.sessions[0]) setRecent(s.sessions[0]);
    });
  }, []);

  return <HomePage indexed={indexed} claudeOk={claudeOk} recentSession={recent} />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<HomeWrapper />} />
            <Route path="characters" element={<CharactersPage />} />
            <Route path="campaigns" element={<CampaignsPage />} />
            <Route path="adventures" element={<AdventuresPage />} />
            <Route path="play" element={<PlayPage />} />
            <Route path="play/:sessionId" element={<PlayPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
