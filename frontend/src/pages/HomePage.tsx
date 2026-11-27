import { Link } from 'react-router-dom';
import { m } from '../lib/framer';
import { BookOpen, Library, Swords, Users, Play, Sparkles } from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import AnimatedPage from '../components/ui/AnimatedPage';
import { fadeUp, staggerContainer } from '../components/ui/motion';
import { useGame } from '../context/GameContext';
import { sessionDisplayTitle, sessionListSubtitle } from '../lib/displayText';

interface Props {
  indexed: boolean | null;
  claudeOk: boolean | null;
  recentSession?: { id: string; name: string; characterName?: string; createdAt?: string } | null;
  sessionsLoaded?: boolean;
}

export default function HomePage({ indexed, claudeOk, recentSession, sessionsLoaded = false }: Props) {
  const { game, gameId } = useGame();

  return (
    <AnimatedPage className="space-y-10">
      <PageHeader title="Auto-DM" subtitle={`${game.label}. ${game.description}`} />
      <HomeStatus indexed={indexed} claudeOk={claudeOk} />
      <HomeStart recentSession={recentSession} sessionsLoaded={sessionsLoaded} />
      <HomeFirstTime gameId={gameId} />
      <HomeNavCards gameId={gameId} />
    </AnimatedPage>
  );
}

function HomeStatus({ indexed, claudeOk }: Pick<Props, 'indexed' | 'claudeOk'>) {
  return (
    <m.div variants={fadeUp} className="flex flex-wrap gap-2">
      {indexed === null || claudeOk === null ? (
        <StatusBadge status="pending" label="Checking status…" />
      ) : (
        <>
          <StatusBadge status={indexed ? 'ok' : 'warn'} label={indexed ? 'Rules index ready' : 'Rules not indexed'} />
          <StatusBadge status={claudeOk ? 'ok' : 'error'} label={claudeOk ? 'Claude configured' : 'Missing API key'} />
        </>
      )}
    </m.div>
  );
}

function HomeStart({ recentSession, sessionsLoaded }: Pick<Props, 'recentSession' | 'sessionsLoaded'>) {
  return (
    <m.div variants={fadeUp} className="grid sm:grid-cols-2 gap-4">
      {recentSession && <ContinuePlayingCard session={recentSession} />}

      <div
        className={`panel-glow p-5 flex flex-col justify-between gap-4 min-h-[10.5rem] ${
          !recentSession && !sessionsLoaded ? 'sm:col-span-2' : ''
        }`}
      >
        <div>
          <p className="label-text mb-1">New story</p>
          <p className="text-sm text-muted">Generate a campaign, adventure, and opening scene in one step.</p>
        </div>
        <Link to="/play?new=1" className="btn-primary inline-flex items-center justify-center gap-2 w-full sm:w-fit">
          <Sparkles size={16} /> Start new campaign
        </Link>
      </div>

      {sessionsLoaded && !recentSession && (
        <div className="panel p-5 flex items-center min-h-[10.5rem]">
          <p className="text-sm text-muted">No sessions yet. Create a character, then start a campaign from Play.</p>
        </div>
      )}
    </m.div>
  );
}

function HomeFirstTime({ gameId }: { gameId: string }) {
  return (
    <m.div variants={fadeUp} className="panel p-5 space-y-2">
      <p className="label-text">First time here?</p>
      <p className="text-sm text-muted leading-relaxed">
        {gameId === 'brambletrek'
          ? 'Create a Gnawborn, then start a campaign from Play. Tap or focus dotted labels for short explanations of Health, Morale, Supplies, Legacy, and journey tools. Books opens the rulebook PDFs.'
          : 'Create a character, then start a campaign from Play. Tap or focus dotted labels on the sheet for Armor Class, proficiency, Exhaustion, and Weapon Mastery. Books opens the 2024 rulebooks on printed page numbers. Tools answers yes/no without inventing the story.'}
      </p>
      <Link to="/characters/new" className="btn-ghost inline-flex w-fit">
        Create a character
      </Link>
    </m.div>
  );
}

function HomeNavCards({ gameId }: { gameId: string }) {
  const cards = [
    {
      to: '/characters',
      icon: Users,
      title: 'Characters',
      desc:
        gameId === 'brambletrek'
          ? 'Create and manage Gnawborn characters.'
          : 'Create and manage PHB 2024 character sheets.',
    },
    {
      to: '/adventures',
      icon: BookOpen,
      title: 'Adventures',
      desc:
        gameId === 'brambletrek' ? 'Browse rulebook and module adventures.' : 'Freeform or Faerûn module adventures.',
    },
    {
      to: '/play',
      icon: Swords,
      title: 'Play',
      desc: 'Start or resume a solo session.',
    },
    {
      to: '/books',
      icon: Library,
      title: 'Books',
      desc:
        gameId === 'brambletrek'
          ? 'Open the Complete Digital Edition and jump to a bookmark.'
          : 'Open the 2024 rulebooks. Page numbers match the printed book.',
    },
  ];

  return (
    <m.div variants={staggerContainer} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {cards.map(({ to, icon: Icon, title, desc }) => (
        <m.div key={to} variants={fadeUp}>
          <Link
            to={to}
            className="panel-glow block p-6 h-full group hover:border-accent/40 hover:shadow-glow transition-[border-color,box-shadow] duration-300"
          >
            <Icon className="text-accent mb-4 group-hover:scale-110 transition-transform duration-300" size={28} />
            <h2 className="display-title text-lg group-hover:opacity-80 transition-opacity">{title}</h2>
            <p className="text-sm text-muted mt-2 leading-relaxed">{desc}</p>
          </Link>
        </m.div>
      ))}
    </m.div>
  );
}

function ContinuePlayingCard({
  session,
}: {
  session: { id: string; name: string; characterName?: string; createdAt?: string };
}) {
  const detail = sessionListSubtitle(session.characterName, session.createdAt);
  return (
    <div className="panel-glow p-5 flex flex-col justify-between gap-4 min-h-[10.5rem]">
      <div>
        <p className="label-text mb-1">Continue playing</p>
        <p className="display-title text-lg">{sessionDisplayTitle(session.name)}</p>
        {detail && <p className="text-sm text-muted mt-1">{detail}</p>}
      </div>
      <Link
        to={`/play/${session.id}`}
        className="btn-primary inline-flex items-center justify-center gap-2 w-full sm:w-fit"
      >
        <Play size={16} /> Resume session
      </Link>
    </div>
  );
}
