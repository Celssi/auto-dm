import { createContext, use, useCallback, useMemo, useRef, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useLocation, useNavigate } from 'react-router-dom';
import { api, type BookBookmark, type BookMeta, type BookState } from '../api/client';
import { matchBookBySource, parseSourcePage } from '../lib/books';
import { useGame } from './GameContext';

interface BookReaderContextType {
  open: boolean;
  bookId: string | null;
  page: number;
  books: BookMeta[];
  booksLoaded: boolean;
  bookState: BookState;
  openBook: (bookId: string, page?: number) => void;
  openReader: () => void;
  openSource: (sourceLabel: string | undefined, page?: string | number) => boolean;
  closeReader: () => void;
  setPage: (page: number) => void;
  toggleBookmark: () => void;
  jumpToBookmark: (bookmark: BookBookmark) => void;
  removeBookmark: (id: string) => void;
}

const BookReaderContext = createContext<BookReaderContextType | undefined>(undefined);

const emptyState: BookState = { bookmarks: [], lastByGame: {} };
const emptyBooks: BookMeta[] = [];

export function BookReaderProvider({ children }: { children: ReactNode }) {
  const { gameId } = useGame();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [bookId, setBookId] = useState<string | null>(null);
  const [page, setPageState] = useState(1);
  const [localState, setLocalState] = useState<BookState | null>(null);
  const persistTimer = useRef<number>(0);
  const booksQuery = useQuery({
    queryKey: ['books', gameId],
    queryFn: () => api.listBooks(gameId),
  });
  const stateQuery = useQuery({
    queryKey: ['book-state'],
    queryFn: () => api.getBookState(),
  });
  const books = booksQuery.data?.books ?? emptyBooks;
  const booksLoaded = booksQuery.isFetched;
  const bookState = localState ?? stateQuery.data ?? emptyState;

  const persistState = useCallback((next: BookState) => {
    setLocalState(next);
    window.clearTimeout(persistTimer.current);
    persistTimer.current = window.setTimeout(() => {
      void api.saveBookState(next).catch(() => undefined);
    }, 250);
  }, []);

  const rememberPage = useCallback(
    (nextBookId: string, nextPage: number) => {
      persistState({
        ...bookState,
        lastByGame: { ...bookState.lastByGame, [gameId]: { book_id: nextBookId, page: nextPage } },
      });
    },
    [bookState, gameId, persistState],
  );

  const openBook = useCallback(
    (nextBookId: string, nextPage?: number) => {
      const resolvedPage = nextPage && nextPage >= 1 ? nextPage : 1;
      setBookId(nextBookId);
      setPageState(resolvedPage);
      setOpen(true);
      rememberPage(nextBookId, resolvedPage);
    },
    [rememberPage],
  );

  const openReader = useCallback(() => {
    const last = bookState.lastByGame[gameId];
    if (last && books.some((book) => book.id === last.book_id)) {
      openBook(last.book_id, last.page);
      return;
    }
    setBookId(null);
    setOpen(true);
  }, [bookState.lastByGame, books, gameId, openBook]);

  const openSource = useCallback(
    (sourceLabel: string | undefined, rawPage?: string | number) => {
      const book = matchBookBySource(books, sourceLabel);
      if (!book) return false;
      openBook(book.id, parseSourcePage(rawPage));
      return true;
    },
    [books, openBook],
  );

  const closeReader = useCallback(() => {
    setOpen(false);
    if (location.pathname.startsWith('/books/')) {
      navigate('/books');
    }
  }, [location.pathname, navigate]);

  const setPage = useCallback(
    (nextPage: number) => {
      const resolved = Math.max(1, Math.floor(nextPage));
      setPageState(resolved);
      if (bookId) rememberPage(bookId, resolved);
    },
    [bookId, rememberPage],
  );

  const toggleBookmark = useCallback(() => {
    if (!bookId) return;
    const existing = bookState.bookmarks.find((mark) => mark.book_id === bookId && mark.page === page);
    const bookmarks = existing
      ? bookState.bookmarks.filter((mark) => mark.id !== existing.id)
      : [
          ...bookState.bookmarks,
          {
            id: crypto.randomUUID().slice(0, 12),
            book_id: bookId,
            page,
            label: `p. ${page}`,
            created_at: new Date().toISOString(),
          },
        ];
    persistState({ ...bookState, bookmarks });
  }, [bookId, bookState, page, persistState]);

  const jumpToBookmark = useCallback(
    (bookmark: BookBookmark) => {
      openBook(bookmark.book_id, bookmark.page);
    },
    [openBook],
  );

  const removeBookmark = useCallback(
    (id: string) => {
      persistState({
        ...bookState,
        bookmarks: bookState.bookmarks.filter((mark) => mark.id !== id),
      });
    },
    [bookState, persistState],
  );

  const value = useMemo(
    () => ({
      open,
      bookId,
      page,
      books,
      booksLoaded,
      bookState,
      openBook,
      openReader,
      openSource,
      closeReader,
      setPage,
      toggleBookmark,
      jumpToBookmark,
      removeBookmark,
    }),
    [
      open,
      bookId,
      page,
      books,
      booksLoaded,
      bookState,
      openBook,
      openReader,
      openSource,
      closeReader,
      setPage,
      toggleBookmark,
      jumpToBookmark,
      removeBookmark,
    ],
  );

  return <BookReaderContext.Provider value={value}>{children}</BookReaderContext.Provider>;
}

export function useBookReader() {
  const context = use(BookReaderContext);
  if (context === undefined) {
    throw new Error('useBookReader must be used within a BookReaderProvider');
  }
  return context;
}
