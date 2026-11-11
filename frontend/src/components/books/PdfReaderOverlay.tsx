import { useEffect, useMemo, useRef, useState } from 'react';
import { Bookmark, BookmarkCheck, ChevronLeft, ChevronRight, Library, Minus, Plus, X } from 'lucide-react';
import { createPortal } from 'react-dom';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { api, type BookBookmark, type BookMeta } from '../../api/client';
import { useBookReader } from '../../context/BookReaderContext';
import { useGame } from '../../context/GameContext';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { getAuthToken } from '../../lib/authToken';
import { pdfPageToPrinted, printedToPdfPage } from '../../lib/books';
import { createRangedPdfSource, type RangedPdfTransport } from '../../lib/pdfRangeSource';

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();

export default function PdfReaderOverlay() {
  const { open, bookId, page, books, bookState, closeReader, openBook, setPage, toggleBookmark, jumpToBookmark } =
    useBookReader();
  const book = books.find((item) => item.id === bookId) ?? null;
  const bookMarks = bookState.bookmarks.filter((mark) => mark.book_id === bookId);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  useFocusTrap(dialogRef, open, closeReader, closeRef);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      ref={dialogRef}
      className="fixed inset-0 z-40 bg-bg flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pdf-reader-title"
      tabIndex={-1}
    >
      <header className="shrink-0 border-b border-border bg-panel px-3 py-2 flex items-center gap-2">
        <button
          ref={closeRef}
          type="button"
          className="btn-ghost min-h-11 min-w-11 px-3"
          onClick={closeReader}
          aria-label="Close reader"
          title="Close reader (Esc)"
        >
          <X size={18} />
        </button>
        <h2 id="pdf-reader-title" className="font-display text-sm text-accent truncate flex-1">
          {book?.label || 'Rulebooks'}
        </h2>
        {book && (
          <button
            type="button"
            className="btn-ghost min-h-11 min-w-11 px-3"
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
    </div>,
    document.body,
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
  const [file, setFile] = useState<RangedPdfTransport | null>(null);
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [pageCount, setPageCount] = useState(1);
  const [loadError, setLoadError] = useState(false);
  const [scale, setScale] = useState(1);
  const [width, setWidth] = useState(640);
  const frameRef = useRef<HTMLDivElement>(null);
  const requestKey = `${book.id}:${gameId}`;
  const visibleFile = loadedKey === requestKey ? file : null;
  const visibleError = loadedKey === requestKey && loadError;
  const visiblePageCount = loadedKey === requestKey ? pageCount : 1;
  const pdfPage = printedToPdfPage(page, book.page_offset);
  const maxPrinted = pdfPageToPrinted(visiblePageCount, book.page_offset);

  useEffect(() => {
    let cancelled = false;
    const transportRef: { current: RangedPdfTransport | null } = { current: null };
    void (async () => {
      try {
        let url = api.bookFileUrl(book.id, gameId);
        let headers: Record<string, string> | undefined;
        try {
          const { ticket } = await api.createBookFileTicket(book.id, gameId);
          url = api.bookFileUrl(book.id, gameId, ticket);
        } catch {
          const token = await getAuthToken();
          if (token) headers = { Authorization: `Bearer ${token}` };
        }
        const next = await createRangedPdfSource(url, headers);
        if (cancelled) {
          next.close();
          return;
        }
        transportRef.current = next;
        setFile(next);
        setLoadError(false);
        setPageCount(1);
        setLoadedKey(requestKey);
      } catch (error) {
        console.error(error);
        if (!cancelled) {
          setLoadError(true);
          setLoadedKey(requestKey);
        }
      }
    })();
    return () => {
      cancelled = true;
      transportRef.current?.close();
    };
  }, [book.id, gameId, requestKey]);

  useEffect(() => {
    const node = frameRef.current;
    if (!node) return;
    const update = () => setWidth(Math.max(280, node.clientWidth - 24));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  // react-pdf Document (suspense=false) reloads whenever `file` / `options` identity
  // changes. An inline `{ range: file }` aborts the transport on every re-render
  // (pageCount, resize, zoom) and leaves requestDataRange as a silent no-op.
  const documentFile = useMemo(() => (visibleFile ? { range: visibleFile } : null), [visibleFile]);
  const documentOptions = useMemo(
    () => ({
      disableAutoFetch: true,
      disableStream: true,
    }),
    [],
  );

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
            {visibleError ? (
              <p className="text-sm text-danger p-6">Could not load this PDF.</p>
            ) : visibleFile ? (
              <Document
                file={documentFile}
                options={documentOptions}
                suspense={false}
                loading={<p className="text-sm text-muted p-6">Loading PDF…</p>}
                error={<p className="text-sm text-danger p-6">Could not load this PDF.</p>}
                onLoadSuccess={({ numPages }) => setPageCount(numPages)}
              >
                <Page
                  pageNumber={Math.min(pdfPage, visiblePageCount)}
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
