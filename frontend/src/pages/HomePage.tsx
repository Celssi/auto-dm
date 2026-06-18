import { Link } from 'react-router-dom';
import { m } from '../lib/framer';
import { BookOpen, Swords, Users, Play, Sparkles } from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import AnimatedPage from '../components/ui/AnimatedPage';
import { fadeUp, staggerContainer } from '../components/ui/motion';

interface Props {
  indexed: boolean;
  claudeOk: boolean;
  recentSession?: { id: string; name: string } | null;
  sessionsLoaded?: boolean;
}

const cards = [
  {
    to: '/characters',
    icon: Users,
    title: 'Characters',
    desc: 'Create and manage PHB 2024 character sheets.',
  },
  {
    to: '/adventures',
    icon: BookOpen,
    title: 'Adventures',
    desc: 'Freeform or Faerûn module adventures.',
  },
  {
    to: '/play',
    icon: Swords,
    title: 'Play',
    desc: 'Start or resume a solo session.',
  },
];

export default function HomePage({ indexed, claudeOk, recentSession, sessionsLoaded = false }: Props) {
  return (
    <AnimatedPage className="max-w-4xl mx-auto space-y-10">
      <PageHeader
        title="Auto-DM"
        subtitle="D&D 5e (2024) solo play with Claude as your Dungeon Master: rules lookup, oracles, and a living journal."
      />

      <m.div variants={fadeUp} className="flex flex-wrap gap-2">
        <StatusBadge status={indexed ? 'ok' : 'warn'} label={indexed ? 'Rules index ready' : 'Rules not indexed'} />
        <StatusBadge status={claudeOk ? 'ok' : 'error'} label={claudeOk ? 'Claude configured' : 'Missing API key'} />
      </m.div>

      <m.div variants={fadeUp} className="grid sm:grid-cols-2 gap-4">
        {recentSession && (
          <div className="panel-glow p-5 sm:col-span-2 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <p className="label-text mb-1">Continue playing</p>
              <p className="font-display text-lg text-gray-100">{recentSession.name}</p>
            </div>
            <Link to={`/play/${recentSession.id}`} className="btn-primary inline-flex items-center gap-2 shrink-0">
              <Play size={16} /> Resume session
            </Link>
          </div>
        )}

        <div className="panel-glow p-5 flex flex-col justify-between gap-4">
          <div>
            <p className="label-text mb-1">New story</p>
            <p className="text-sm text-muted">Generate a campaign, adventure, and opening scene in one step.</p>
          </div>
          <Link to="/play?new=1" className="btn-primary inline-flex items-center gap-2 w-fit">
            <Sparkles size={16} /> Start new campaign
          </Link>
        </div>

        {!sessionsLoaded
          ? null
          : !recentSession && (
              <div className="panel p-5 flex items-center">
                <p className="text-sm text-muted">
                  No active sessions yet. Start a new campaign or create a character first.
                </p>
              </div>
            )}
      </m.div>

      <m.div variants={staggerContainer} className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map(({ to, icon: Icon, title, desc }) => (
          <m.div key={to} variants={fadeUp}>
            <Link
              to={to}
              className="panel-glow block p-6 h-full group hover:border-accent/40 hover:shadow-glow transition-all duration-300"
            >
              <Icon className="text-accent mb-4 group-hover:scale-110 transition-transform duration-300" size={28} />
              <h2 className="font-display font-semibold text-lg text-gray-100 group-hover:text-accent transition-colors">
                {title}
              </h2>
              <p className="text-sm text-muted mt-2 leading-relaxed">{desc}</p>
            </Link>
          </m.div>
        ))}
      </m.div>
    </AnimatedPage>
  );
}
