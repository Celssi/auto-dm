import ReactMarkdown from 'react-markdown';

interface Props {
  content: string;
  className?: string;
}

export default function MarkdownContent({ content, className = '' }: Props) {
  if (!content.trim()) return null;

  return (
    <div className={`prose-dark ${className}`.trim()}>
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
