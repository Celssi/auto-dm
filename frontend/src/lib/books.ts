import type { BookMeta } from '../api/client';

export function printedToPdfPage(printed: number, pageOffset: number): number {
  return Math.max(1, printed + pageOffset);
}

export function pdfPageToPrinted(pdfPage: number, pageOffset: number): number {
  return Math.max(1, pdfPage - pageOffset);
}

export function parseSourcePage(page: string | number | undefined): number | undefined {
  if (typeof page === 'number' && Number.isFinite(page) && page >= 1) return Math.floor(page);
  if (typeof page !== 'string') return undefined;
  const match = page.match(/(\d+)/);
  if (!match) return undefined;
  const value = Number(match[1]);
  return Number.isFinite(value) && value >= 1 ? value : undefined;
}

export function matchBookBySource(books: BookMeta[], sourceLabel: string | undefined): BookMeta | undefined {
  const needle = sourceLabel?.trim().toLowerCase();
  if (!needle) return undefined;
  return (
    books.find((book) => book.aliases.includes(needle) || book.label.toLowerCase() === needle) ||
    books.find((book) => book.label.toLowerCase().includes(needle) || needle.includes(book.label.toLowerCase()))
  );
}
