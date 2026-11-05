import { pdfjs } from 'react-pdf';

export type RangedPdfTransport = InstanceType<typeof pdfjs.PDFDataRangeTransport> & {
  /** Permanent teardown when leaving the book / unmounting the reader. */
  close: () => void;
};

/** Build a ranged PDF source that stays under Cloud Run's ~32 MiB response cap. */
export async function createRangedPdfSource(
  url: string,
  httpHeaders?: Record<string, string>,
): Promise<RangedPdfTransport> {
  const head = await fetch(url, { method: 'HEAD', headers: httpHeaders, credentials: 'omit' });
  if (!head.ok) {
    throw new Error(`Could not read PDF size (${head.status})`);
  }
  const length = Number(head.headers.get('Content-Length'));
  if (!Number.isFinite(length) || length <= 0) {
    throw new Error('PDF size header missing');
  }

  class TicketRangeTransport extends pdfjs.PDFDataRangeTransport {
    /** Soft-cancel only: react-pdf Strict Mode / ResourceCache dispose() aborts then
     * remounts Document with the same transport. A permanent kill makes
     * requestDataRange a silent no-op → endless "Loading PDF…". */
    #controllers = new Set<AbortController>();
    #closed = false;

    requestDataRange(begin: number, end: number) {
      if (this.#closed) return;
      const controller = new AbortController();
      this.#controllers.add(controller);
      void (async () => {
        try {
          const res = await fetch(url, {
            headers: {
              ...httpHeaders,
              Range: `bytes=${begin}-${end - 1}`,
            },
            credentials: 'omit',
            signal: controller.signal,
          });
          if (!(res.status === 200 || res.status === 206)) {
            throw new Error(`PDF range failed (${res.status})`);
          }
          const chunk = new Uint8Array(await res.arrayBuffer());
          if (!this.#closed) {
            this.onDataRange(begin, chunk);
          }
        } catch (error) {
          if (controller.signal.aborted || this.#closed) return;
          console.error(error);
          if (!this.#closed) {
            this.onDataRange(begin, null);
          }
        } finally {
          this.#controllers.delete(controller);
        }
      })();
    }

    abort() {
      for (const controller of this.#controllers) {
        controller.abort();
      }
      this.#controllers.clear();
      // Do not call super.abort() — that permanently rejects transportReady and
      // breaks remounts that reuse this instance.
    }

    /** Permanent teardown when leaving the book / unmounting the reader. */
    close() {
      this.#closed = true;
      this.abort();
    }
  }

  return new TicketRangeTransport(length, new Uint8Array(0)) as RangedPdfTransport;
}
