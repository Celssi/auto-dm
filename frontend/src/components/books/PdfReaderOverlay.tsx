import { useEffect, useMemo, useRef, useState } from 'react';
import { Bookmark, BookmarkCheck, ChevronLeft, ChevronRight, Library, Minus, Plus, X } from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { api, type BookBookmark, type BookMeta } from '../../api/client';
import { useBookReader } from '../../context/BookReaderContext';
import { useGame } from '../../context/GameContext';
import { getAuthToken } from '../../lib/authToken';
import { pdfPageToPrinted, printedToPdfPage } from '../../lib/books';

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();

export default function PdfReaderOverlay() {
  const { open, bookId, page, books, bookState, closeReader, openBook, setPage, toggleBookmark, jumpToBookmark } =
    useBookReader();
  const book = books.find((item) => item.id === bookId) ?? null;
  const bookMarks = bookState.bookmarks.filter((mark) => mark.book_id === bookId);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 bg-bg flex flex-col">
      <header className="shrink-0 border-b border-border bg-panel px-3 py-2 flex items-center gap-2">
        <button type="button" className="btn-ghost min-h-11 px-3" onClick={closeReader} aria-label="Close reader">
          <X size={18} />
        </button>
        <p className="font-display text-sm text-accent truncate flex-1">{book?.label || 'Rulebooks'}</p>
        {book && (
          <button
            type="button"
            className="btn-ghost min-h-11 px-3"
            onClick={toggleBookmark}
            aria-label={bookMarks.some((mark) => mark.page === page) ? 'Remove bookmark' : 'Add bookmark'}
          >
            {bookMarks.some((mark) => mark.page === page) ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
          </button>
        )}
      </header>
      {book ? (
        <PdfPages book={book} page={page} bookmarks={bookMarks} onPage={setPage} onJump={jumpToBookmark} />
      ) : (
        <BookPicker books={books} onOpen={openBook} />
      )}
    </div>
  );
}

function BookPicker({ books, onOpen }: { books: BookMeta[]; onOpen: (id: string) => void }) {
  if (books.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center">
        <p className="text-sm text-muted">No rulebook PDFs are available for this game yet.</p>
      </div>
    );
  }
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-2">
      <p className="label-text px-1">Open a rulebook</p>
      {books.map((book) => (
        <button
          key={book.id}
          type="button"
          className="panel w-full text-left p-4 hover:border-accent/30"
          onClick={() => onOpen(book.id)}
        >
          <span className="font-medium text-gray-100">{book.label}</span>
        </button>
      ))}
    </div>
  );
}

function PdfPages({
  book,
  page,
  bookmarks,
  onPage,
  onJump,
}: {
  book: BookMeta;
  page: number;
  bookmarks: BookBookmark[];
  onPage: (page: number) => void;
  onJump: (bookmark: BookBookmark) => void;
}) {
  const { gameId } = useGame();
  const [token, setToken] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [pageCount, setPageCount] = useState(1);
  const [scale, setScale] = useState(1);
  const [width, setWidth] = useState(640);
  const frameRef = useRef<HTMLDivElement>(null);
  const pdfPage = printedToPdfPage(page, book.page_offset);
  const maxPrinted = pdfPageToPrinted(pageCount, book.page_offset);

  useEffect(() => {
    let cancelled = false;
    void getAuthToken()
      .then((value) => {
        if (!cancelled) setToken(value);
      })
      .finally(() => {
        if (!cancelled) setAuthReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const node = frameRef.current;
    if (!node) return;
    const update = () => setWidth(Math.max(280, node.clientWidth - 24));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const file = useMemo(() => {
    if (!authReady) return null;
    const url = api.bookFileUrl(book.id, gameId);
    return token ? { url, httpHeaders: { Authorization: `Bearer ${token}` } } : { url };
  }, [authReady, book.id, gameId, token]);

  const go = (next: number) => onPage(Math.min(maxPrinted, Math.max(1, next)));

  return (
    <>
      <div className="shrink-0 border-b border-border bg-panel px-3 py-2 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="btn-ghost min-h-11 px-3"
          disabled={page <= 1}
          onClick={() => go(page - 1)}
          aria-label="Previous page"
        >
          <ChevronLeft size={18} />
        </button>
        <label className="text-xs text-muted inline-flex items-center gap-2">
          Page
          <input
            type="number"
            min={1}
            max={maxPrinted}
            value={page}
            onChange={(event) => go(Number(event.target.value) || 1)}
            className="w-16 min-h-11 rounded-lg border border-border bg-bg px-2 text-sm text-gray-100"
          />
          of {maxPrinted}
        </label>
        <button
          type="button"
          className="btn-ghost min-h-11 px-3"
          disabled={page >= maxPrinted}
          onClick={() => go(page + 1)}
          aria-label="Next page"
        >
          <ChevronRight size={18} />
        </button>
        <div className="ml-auto flex items-center gap-1">
          <button
            type="button"
            className="btn-ghost min-h-11 px-3"
            onClick={() => setScale((value) => Math.max(0.6, Math.round((value - 0.1) * 10) / 10))}
            aria-label="Zoom out"
          >
            <Minus size={16} />
          </button>
          <span className="text-xs text-muted w-10 text-center">{Math.round(scale * 100)}%</span>
          <button
            type="button"
            className="btn-ghost min-h-11 px-3"
            onClick={() => setScale((value) => Math.min(2.4, Math.round((value + 0.1) * 10) / 10))}
            aria-label="Zoom in"
          >
            <Plus size={16} />
          </button>
        </div>
      </div>
      <div className="flex-1 min-h-0 flex flex-col md:flex-row">
        <div ref={frameRef} className="flex-1 min-h-0 overflow-auto bg-bg-elevated">
          <div className="flex justify-center py-3">
            {file ? (
              <Document
                file={file}
                suspense={false}
                loading={<p className="text-sm text-muted p-6">Loading PDF…</p>}
                error={<p className="text-sm text-danger p-6">Could not load this PDF.</p>}
                onLoadSuccess={({ numPages }) => setPageCount(numPages)}
              >
                <Page
                  pageNumber={Math.min(pdfPage, pageCount)}
                  width={width}
                  scale={scale}
                  loading={<p className="text-sm text-muted p-6">Rendering page…</p>}
                />
              </Document>
            ) : (
              <p className="text-sm text-muted p-6">Preparing reader…</p>
            )}
          </div>
        </div>
        {bookmarks.length > 0 && (
          <aside className="shrink-0 md:w-64 border-t md:border-t-0 md:border-l border-border bg-panel p-3 max-h-40 md:max-h-none overflow-y-auto">
            <p className="label-text mb-2 inline-flex items-center gap-1.5">
              <Library size={12} /> Bookmarks
            </p>
            <ul className="space-y-1">
              {bookmarks
                .toSorted((a, b) => a.page - b.page)
                .map((mark) => (
                  <li key={mark.id}>
                    <button
                      type="button"
                      className={`w-full text-left rounded-lg px-3 py-2 text-sm min-h-11 ${
                        mark.page === page ? 'bg-accent/15 text-accent' : 'text-gray-200 hover:bg-panel-hover'
                      }`}
                      onClick={() => onJump(mark)}
                    >
                      {mark.label || `p. ${mark.page}`}
                    </button>
                  </li>
                ))}
            </ul>
          </aside>
        )}
      </div>
    </>
  );
}
