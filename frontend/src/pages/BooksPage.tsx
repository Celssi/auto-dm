import { useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Bookmark, Library } from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import ListCard from '../components/ui/ListCard';
import EmptyState from '../components/ui/EmptyState';
import ListLoading from '../components/ui/ListLoading';
import AnimatedPage from '../components/ui/AnimatedPage';
import { fadeUp, staggerContainer } from '../components/ui/motion';
import { m } from '../lib/framer';
import { useGame } from '../context/GameContext';
import { useBookReader } from '../context/BookReaderContext';

export default function BooksPage() {
  const navigate = useNavigate();
  const { bookId: rawBookId } = useParams();
  const { game, gameId } = useGame();
  const { books, booksLoaded, bookState, openBook, jumpToBookmark, removeBookmark } = useBookReader();
  const bookId = rawBookId ? decodeURIComponent(rawBookId) : undefined;
  const last = bookState.lastByGame[gameId];
  const lastBook = last ? books.find((book) => book.id === last.book_id) : undefined;
  const marks = bookState.bookmarks.filter((mark) => books.some((book) => book.id === mark.book_id));

  const openedRouteRef = useRef<string | null>(null);
  useEffect(() => {
    if (!bookId) openedRouteRef.current = null;
  }, [bookId]);
  useEffect(() => {
    if (!bookId || !booksLoaded) return;
    if (openedRouteRef.current === bookId) return;
    if (!books.some((book) => book.id === bookId)) return;
    openedRouteRef.current = bookId;
    const page = new URLSearchParams(window.location.search).get('page');
    openBook(bookId, page ? Number(page) || undefined : last?.book_id === bookId ? last.page : undefined);
  }, [bookId, books, booksLoaded, last, openBook]);

  const open = (id: string, page?: number) => {
    navigate(`/books/${encodeURIComponent(id)}`);
    openBook(id, page);
  };

  return (
    <AnimatedPage className="space-y-8">
      <PageHeader title="Books" subtitle={`Open ${game.label} rulebooks and jump to a bookmark.`} />

      {lastBook && (
        <m.div variants={fadeUp}>
          <button
            type="button"
            className="panel-glow w-full text-left p-5"
            onClick={() => open(lastBook.id, last?.page)}
          >
            <p className="label-text mb-1">Continue reading</p>
            <p className="display-title text-lg">{lastBook.label}</p>
            <p className="text-sm text-muted mt-1">Page {last?.page ?? 1}</p>
          </button>
        </m.div>
      )}

      <section className="space-y-3">
        <h2 className="section-heading">Rulebooks</h2>
        {!booksLoaded ? (
          <ListLoading />
        ) : books.length === 0 ? (
          <EmptyState
            icon={<Library size={32} />}
            title="No PDFs available"
            description="Rulebook files for this game are not in storage yet."
          />
        ) : (
          <m.div variants={staggerContainer} className="grid gap-3 sm:grid-cols-2">
            {books.map((book) => (
              <ListCard
                key={book.id}
                title={book.label}
                subtitle={book.faction}
                onClick={() => open(book.id, last?.book_id === book.id ? last.page : 1)}
              />
            ))}
          </m.div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="section-heading inline-flex items-center gap-2">
          <Bookmark size={14} /> Bookmarks
        </h2>
        {marks.length === 0 ? (
          <p className="text-sm text-muted">Bookmark a page while reading to find it later.</p>
        ) : (
          <ul className="space-y-2">
            {marks
              .toSorted((a, b) => a.book_id.localeCompare(b.book_id) || a.page - b.page)
              .map((mark) => {
                const book = books.find((item) => item.id === mark.book_id);
                return (
                  <li key={mark.id} className="panel p-3 flex items-center gap-3">
                    <button type="button" className="flex-1 text-left min-h-11" onClick={() => jumpToBookmark(mark)}>
                      <p className="text-sm text-gray-100">{mark.label || `p. ${mark.page}`}</p>
                      <p className="text-xs text-muted">{book?.label || mark.book_id}</p>
                    </button>
                    <button type="button" className="btn-ghost text-sm" onClick={() => removeBookmark(mark.id)}>
                      Remove
                    </button>
                  </li>
                );
              })}
          </ul>
        )}
      </section>
    </AnimatedPage>
  );
}
