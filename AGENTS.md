# Auto-DM - AI Assistant Guide

Auto-DM is a D&D 5e (2024) solo play app: FastAPI backend, React frontend, Claude as DM.

## Copy and typography

**Do not use em dashes (—) or en dashes (–) in user-facing text.**

This applies to:

- React UI copy (labels, subtitles, placeholders, empty states, buttons)
- DM narration and chat responses shown to the player
- Bootstrap/opening scenes and adventure summaries intended for play
- PDF export titles and sheet labels

Use instead:

- **Commas or periods** for aside or continuation: "Generate an outline, then play" not "outline — then play"
- **Hyphen-minus (`-`)** for empty fields on character sheets
- **Hyphen-minus** for numeric ranges: `30-60 s`, `1-8`
- **Colon** for titles: `Auto-DM: D&D 5e Solo`
- **Pipe or comma** where a separator is needed: `Name | D&D 5e Character Sheet`

Internal code comments and debug logs may use normal punctuation; player-visible strings may not.

When editing frontend empty-value placeholders, use `EMPTY_FIELD` from `frontend/src/lib/displayText.ts`.

## Key paths

| Area | Path |
|------|------|
| DM graph | `backend/dm/graph.py` |
| System prompt | `backend/dm/prompts.py` |
| Campaign bootstrap | `backend/dm/campaign_bootstrap.py` |
| Storage | `backend/storage.py`, `backend/journal_storage.py` |
| Play UI | `frontend/src/pages/PlayPage.tsx` |
| Campaigns UI | `frontend/src/pages/CampaignsPage.tsx` |

## Running locally

```bash
./scripts/start-app.sh
```

API: http://127.0.0.1:8000 · UI: http://localhost:5173
