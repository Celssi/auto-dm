# Curated D&D 5e data

Static character-creation and oracle data extracted from rulebooks.

## Files

| File | Source | Scope |
|------|--------|--------|
| `dnd5e_glossary.yaml` | PHB 2024 OCR | Full spell, skill, and feat descriptions for UI tooltips |
| `dnd5e_classes.yaml` | PHB 2024 | 12 classes, spell slot tables |
| `dnd5e_species.yaml` | PHB 2024 | Core species |
| `dnd5e_backgrounds.yaml` | PHB 2024 | 16 backgrounds |
| `dnd5e_spells.yaml` | PHB 2024 | Spell lists by class |
| `dnd5e_equipment.yaml` | PHB 2024 | Armor, weapons, starting gear |
| `dnd5e_skills.yaml` | PHB 2024 | Skills, alignments, standard array |
| `dnd5e_oracle.yaml` | Solo play | d6 oracle table |
| `dnd5e_faerun.yaml` | Heroes of Faerûn | **Optional** — subclasses, backgrounds, regional gear |
| `dnd5e_multiclass.yaml` | PHB 2024 | Multiclass prerequisites and caster rules |
| `dnd5e_class_features.yaml` | PHB 2024 | Base class features by level (1–20) |
| `dnd5e_subclass_features.yaml` | PHB + HoF | Subclass features by level |

Regenerate feature YAML after edits:

```bash
python -m scripts.build_feature_yaml
python -m scripts.build_glossary_db   # spell/skill/feat tooltip text from OCR
```

## Faerûn (conditional)

Heroes of Faerûn adds player options (subclasses, backgrounds, feats, spells). Adventures in Faerûn is mainly adventure content and is served via **RAG** (`heroes_faerun`, `adventures_faerun` factions), not this folder.

Faerûn curated data is merged when:

- `GET /api/characters/options?include_faerun=true`, or
- Global Settings → “Include Faerûn supplements”, or
- Character wizard → Campaign = **Faerûn**

Core PHB files stay unchanged. Faerûn entries use `source: faerun` on backgrounds.

Background mechanics in `dnd5e_faerun.yaml` are starter values — verify against `dnd5e/heroes_faerun.pdf` or rules search before relying on exact feats/skills.

## Adding content

1. Edit the relevant YAML (or `dnd5e_faerun.yaml` for supplement options).
2. Run `python -m scripts.validate_dnd5e_character` and `python -m scripts.validate_glossary`.
3. Restart the API (cached loaders reset on process restart).

Future: a script could extract Faerûn backgrounds from PDF/OCR into this file automatically.

```bash
# Audit curated YAML vs PDFs (needs ANTHROPIC_API_KEY; RAG index recommended)
python -m scripts.audit_curated
python -m scripts.audit_curated --include-faerun

# Extract / fix backgrounds from PDF
python -m scripts.extract_backgrounds --source heroes_faerun --dry-run
python -m scripts.extract_backgrounds --source player --audit-only
python -m scripts.extract_backgrounds --source heroes_faerun --apply
```
