import { Link } from "react-router-dom";
import { BookOpen, Swords, Users, Play } from "lucide-react";

interface Props {
  indexed: boolean;
  claudeOk: boolean;
  recentSession?: { id: string; name: string } | null;
}

export default function HomePage({ indexed, claudeOk, recentSession }: Props) {
  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <header>
        <h1 className="text-3xl font-bold text-accent">Auto-DM</h1>
        <p className="text-muted mt-2">D&D 5e (2024) solo play with Claude Opus as your Dungeon Master.</p>
      </header>

      <div className="flex gap-4 text-sm">
        <span className={indexed ? "text-green-400" : "text-yellow-400"}>
          Rules index: {indexed ? "ready" : "not indexed — run ingest"}
        </span>
        <span className={claudeOk ? "text-green-400" : "text-red-400"}>
          Claude: {claudeOk ? "configured" : "missing API key"}
        </span>
      </div>

      {recentSession && (
        <div className="panel p-4">
          <p className="text-sm text-muted mb-2">Continue playing</p>
          <Link to={`/play/${recentSession.id}`} className="btn-primary inline-flex items-center gap-2">
            <Play size={16} /> {recentSession.name}
          </Link>
        </div>
      )}

      <div className="panel p-4">
        <p className="text-sm text-muted mb-2">Ready for a fresh story?</p>
        <Link to="/play?new=1" className="btn-primary inline-flex items-center gap-2">
          <Play size={16} /> Start new campaign
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/characters" className="panel p-6 hover:border-accent transition-colors">
          <Users className="text-accent mb-3" size={28} />
          <h2 className="font-semibold">Characters</h2>
          <p className="text-sm text-muted mt-1">Create and manage PHB 2024 character sheets.</p>
        </Link>
        <Link to="/adventures" className="panel p-6 hover:border-accent transition-colors">
          <BookOpen className="text-accent mb-3" size={28} />
          <h2 className="font-semibold">Adventures</h2>
          <p className="text-sm text-muted mt-1">Freeform or Faerûn module adventures.</p>
        </Link>
        <Link to="/play" className="panel p-6 hover:border-accent transition-colors">
          <Swords className="text-accent mb-3" size={28} />
          <h2 className="font-semibold">Play</h2>
          <p className="text-sm text-muted mt-1">Start or resume a solo session.</p>
        </Link>
      </div>
    </div>
  );
}
