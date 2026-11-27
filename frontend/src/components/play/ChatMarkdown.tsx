import { Children, cloneElement, isValidElement, useMemo, type JSX, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import JournalTip from './JournalTip';
import { buildEntityMatcher, entityByMatchedName, type JournalEntity } from '../../lib/journalTips';

const EMPTY_ENTITIES: JournalEntity[] = [];

function enrichText(
  text: string,
  entities: JournalEntity[],
  matcher: RegExp | null,
  keyPrefix: string,
  linkedNames: Set<string>,
): ReactNode {
  if (!matcher || !text) return text;
  const local = new RegExp(matcher.source, matcher.flags);
  local.lastIndex = 0;
  const parts = text.split(local);
  return parts.map((part, i) => {
    const entity = entityByMatchedName(entities, part);
    if (entity && i % 2 === 1) {
      const seenKey = entity.name.toLowerCase();
      if (linkedNames.has(seenKey)) return part;
      linkedNames.add(seenKey);
      return <JournalTip key={`${keyPrefix}-${entity.kind}-${entity.name}`} entity={entity} text={part} />;
    }
    return part;
  });
}

function enrichChildren(
  children: ReactNode,
  entities: JournalEntity[],
  matcher: RegExp | null,
  keyPrefix: string,
  linkedNames: Set<string>,
): ReactNode {
  return Children.map(children, (child, index) => {
    const childPrefix = `${keyPrefix}-${index}`;
    if (typeof child === 'string') {
      return enrichText(child, entities, matcher, childPrefix, linkedNames);
    }
    if (isValidElement<{ children?: ReactNode }>(child) && child.props.children) {
      return cloneElement(child, {}, enrichChildren(child.props.children, entities, matcher, childPrefix, linkedNames));
    }
    return child;
  });
}

interface Props {
  content: string;
  entities?: JournalEntity[];
}

type HtmlTag = Extract<keyof JSX.IntrinsicElements, string>;

export default function ChatMarkdown({ content, entities = EMPTY_ENTITIES }: Props) {
  const matcher = useMemo(() => buildEntityMatcher(entities), [entities]);
  const linkedNames = new Set<string>();
  const wrap = (tag: HtmlTag) => {
    const Tag = tag;
    return ({ children }: { children?: ReactNode }) => {
      const inner = enrichChildren(children, entities, matcher, tag, linkedNames);
      return <Tag>{inner}</Tag>;
    };
  };
  const components = {
    p: wrap('p'),
    li: wrap('li'),
    strong: wrap('strong'),
    em: wrap('em'),
    h1: wrap('h1'),
    h2: wrap('h2'),
    h3: wrap('h3'),
  };

  return (
    <div className="chat-markdown">
      <ReactMarkdown components={components}>{content}</ReactMarkdown>
    </div>
  );
}
