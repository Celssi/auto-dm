import { m } from '../../lib/framer';
import ReactMarkdown from 'react-markdown';
import type { AdventureFull } from '../../api/client';

export default function AdventureDetailPanel({ adventure }: { adventure: AdventureFull }) {
  return (
    <m.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      className="panel-glow p-5 space-y-4 overflow-y-auto max-h-[75vh]"
    >
      <h2 className="font-display text-xl text-gray-100">{adventure.name}</h2>
      <div className="prose-dark">
        <ReactMarkdown>{adventure.outline || '_No outline yet._'}</ReactMarkdown>
      </div>
      {adventure.log && (
        <>
          <h3 className="section-heading pt-2">Adventure log</h3>
          <div className="prose-dark text-xs rounded-lg border border-border bg-bg/40 p-4">
            <ReactMarkdown>{adventure.log}</ReactMarkdown>
          </div>
        </>
      )}
    </m.div>
  );
}
