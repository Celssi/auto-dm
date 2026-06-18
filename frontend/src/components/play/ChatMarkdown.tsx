import { Children, cloneElement, isValidElement, useCallback, useMemo, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import JournalTip from './JournalTip';
import { buildEntityMatcher, entityByMatchedName, type JournalEntity } from '../../lib/journalTips';

const EMPTY_ENTITIES: JournalEntity[] = [];

function enrichText(text: string, entities: JournalEntity[], matcher: RegExp | null, keyPrefix: string): ReactNode {
  if (!matcher || !text) return text;
  const parts = text.split(matcher);
  return parts.map((part, i) => {
    const entity = entityByMatchedName(entities, part);
    if (entity && i % 2 === 1) {
      return (
        <JournalTip
          key={`${keyPrefix}-${entity ? `${entity.kind}-${entity.name}` : part}`}
          entity={entity}
          text={part}
        />
      );
    }
    return part;
  });
}

function enrichChildren(
  children: ReactNode,
  entities: JournalEntity[],
  matcher: RegExp | null,
  keyPrefix: string,
): ReactNode {
  return Children.map(children, (child, index) => {
    const key = `${keyPrefix}-${index}`;
    if (typeof child === 'string') {
      return enrichText(child, entities, matcher, key);
    }
    if (isValidElement(child) && child.props.children) {
      return cloneElement(child, { key: child.key ?? key }, enrichChildren(child.props.children, entities, matcher, key));
    }
    return child;
  });
}

interface Props {
  content: string;
  entities?: JournalEntity[];
}

export default function ChatMarkdown({ content, entities = EMPTY_ENTITIES }: Props) {
  const matcher = useMemo(() => buildEntityMatcher(entities), [entities]);

  const wrap = useCallback(
    (Tag: keyof JSX.IntrinsicElements) =>
      ({ children }: { children?: ReactNode }) => {
        const inner = enrichChildren(children, entities, matcher, Tag);
        return <Tag>{inner}</Tag>;
      },
    [entities, matcher],
  );

  const components = useMemo(
    () => ({
      p: wrap('p'),
      li: wrap('li'),
      strong: wrap('strong'),
      em: wrap('em'),
      h1: wrap('h1'),
      h2: wrap('h2'),
      h3: wrap('h3'),
    }),
    [wrap],
  );

  return (
    <div className="chat-markdown">
      <ReactMarkdown components={components}>{content}</ReactMarkdown>
    </div>
  );
}
