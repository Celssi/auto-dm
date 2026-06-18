#!/usr/bin/env bash
# Full auto-dm setup: index all PDFs (PHB + DMG + MM + Faerûn) with OCR, then audit curated YAML.
# First run can take several hours.
#
#   ./scripts/ingest-full.sh              # everything (default)
#   ./scripts/ingest-full.sh --skip-audit   # ingest only
#   ./scripts/ingest-full.sh --no-ocr       # skip OCR fallback on ingest (native text only)
#   ./scripts/ingest-full.sh --ocr          # force re-OCR on ingest (audit always reuses cache)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Virtualenv missing. Create it first:"
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found. Install from https://ollama.com"
  exit 1
fi

if ! ollama list 2>/dev/null | grep -q 'nomic-embed-text'; then
  echo "Pulling embedding model nomic-embed-text..."
  ollama pull nomic-embed-text
fi

if ! command -v tesseract >/dev/null 2>&1; then
  echo "WARNING: Tesseract not installed — scanned PDFs (PHB, HoF) will index poorly."
  echo "  brew install tesseract"
fi

FORCE_INGEST_OCR=0
SKIP_INGEST_OCR=0
SKIP_AUDIT=0
EXTRA_INGEST_ARGS=()

for arg in "$@"; do
  case "$arg" in
    --skip-audit)
      SKIP_AUDIT=1
      ;;
    --no-ocr)
      SKIP_INGEST_OCR=1
      ;;
    --ocr)
      FORCE_INGEST_OCR=1
      ;;
    *)
      EXTRA_INGEST_ARGS+=("$arg")
      ;;
  esac
done

INGEST_ARGS=(--include-faerun)
AUDIT_ARGS=(--include-faerun)
if [[ "$FORCE_INGEST_OCR" == "1" ]]; then
  INGEST_ARGS+=(--ocr)
fi
if [[ "$SKIP_INGEST_OCR" == "1" ]]; then
  INGEST_ARGS+=(--no-ocr)
fi
if ((${#EXTRA_INGEST_ARGS[@]})); then
  INGEST_ARGS+=("${EXTRA_INGEST_ARGS[@]}")
fi

echo "=== Auto-DM full ingest ==="
echo "Project: $ROOT"
echo "PDFs:    PHB + DMG + MM + Faerûn"
echo "OCR:     ingest=$([[ "$FORCE_INGEST_OCR" == "1" ]] && echo 'force refresh' || ([[ "$SKIP_INGEST_OCR" == "1" ]] && echo 'disabled' || echo 'use cache')); audit=use cache"
echo "Glossary: rebuilt from PHB OCR after ingest"
echo "Audit:   $([[ "$SKIP_AUDIT" == "1" ]] && echo 'skipped' || echo 'structural + glossary + PDF backgrounds')"
echo ""

export PYTHONUNBUFFERED=1
python -m scripts.ingest "${INGEST_ARGS[@]}"

if [[ "$SKIP_AUDIT" == "1" ]]; then
  echo ""
  echo "Ingest done. Start the app with: ./scripts/start-app.sh"
  exit 0
fi

echo ""
echo "=== Curated data audit ==="
python -m scripts.audit_curated "${AUDIT_ARGS[@]}"

echo ""
echo "Done. Start the app with: ./scripts/start-app.sh"
