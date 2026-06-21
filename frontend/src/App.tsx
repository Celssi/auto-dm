import { useEffect, useState } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import { GlossaryProvider } from './context/GlossaryContext';
import HomePage from './pages/HomePage';
import CharactersPage from './pages/CharactersPage';
import CampaignsPage from './pages/CampaignsPage';
import AdventuresPage from './pages/AdventuresPage';
import PlayPage from './pages/PlayPage';
import SettingsPage from './pages/SettingsPage';
import { api } from './api/client';

import { LazyMotion, domAnimation } from './lib/framer';

const queryClient = new QueryClient();

function MotionProvider({ children }: { children: React.ReactNode }) {
  return (
    <LazyMotion features={domAnimation} strict>
      {children}
    </LazyMotion>
  );
}

function HomeWrapper() {
  const [indexed, setIndexed] = useState(false);
  const [claudeOk, setClaudeOk] = useState(false);
  const [recent, setRecent] = useState<{ id: string; name: string } | null>(null);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);

  useEffect(() => {
    api.health().then((h) => {
      setIndexed(h.indexed);
      setClaudeOk(h.claude_configured);
    });
    api
      .listSessions()
      .then((s) => {
        if (s.sessions[0]) setRecent(s.sessions[0]);
      })
      .finally(() => setSessionsLoaded(true));
  }, []);

  return <HomePage indexed={indexed} claudeOk={claudeOk} recentSession={recent} sessionsLoaded={sessionsLoaded} />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionProvider>
        <GlossaryProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<HomeWrapper />} />
                <Route path="characters" element={<CharactersPage />} />
                <Route path="characters/new" element={<CharactersPage />} />
                <Route path="characters/:characterId/edit" element={<CharactersPage />} />
                <Route path="characters/:characterId" element={<CharactersPage />} />
                <Route path="campaigns" element={<CampaignsPage />} />
                <Route path="campaigns/new" element={<CampaignsPage />} />
                <Route path="campaigns/:campaignId/:tab" element={<CampaignsPage />} />
                <Route path="campaigns/:campaignId" element={<CampaignsPage />} />
                <Route path="adventures" element={<AdventuresPage />} />
                <Route path="adventures/new" element={<AdventuresPage />} />
                <Route path="adventures/:adventureId" element={<AdventuresPage />} />
                <Route path="play" element={<PlayPage />} />
                <Route path="play/:sessionId" element={<PlayPage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </GlossaryProvider>
      </MotionProvider>
    </QueryClientProvider>
  );
}
