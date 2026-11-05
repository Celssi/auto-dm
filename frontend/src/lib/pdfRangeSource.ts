import { pdfjs } from 'react-pdf';

/** Build a ranged PDF source that stays under Cloud Run's ~32 MiB response cap. */
export async function createRangedPdfSource(
  url: string,
  httpHeaders?: Record<string, string>,
): Promise<InstanceType<typeof pdfjs.PDFDataRangeTransport>> {
  const head = await fetch(url, { method: 'HEAD', headers: httpHeaders, credentials: 'omit' });
  if (!head.ok) {
    throw new Error(`Could not read PDF size (${head.status})`);
  }
  const length = Number(head.headers.get('Content-Length'));
  if (!Number.isFinite(length) || length <= 0) {
    throw new Error('PDF size header missing');
  }

  class TicketRangeTransport extends pdfjs.PDFDataRangeTransport {
    #aborted = false;
    #controllers = new Set<AbortController>();

    requestDataRange(begin: number, end: number) {
      if (this.#aborted) return;
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
          if (!this.#aborted) {
            this.onDataRange(begin, chunk);
          }
        } catch (error) {
          if (controller.signal.aborted || this.#aborted) return;
          console.error(error);
          if (!this.#aborted) {
            this.onDataRange(begin, null);
          }
        } finally {
          this.#controllers.delete(controller);
        }
      })();
    }

    abort() {
      this.#aborted = true;
      for (const controller of this.#controllers) {
        controller.abort();
      }
      this.#controllers.clear();
    }
  }

  return new TicketRangeTransport(length, new Uint8Array(0));
}
