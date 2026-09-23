"""Ensure dm/ core is game-agnostic."""

from __future__ import annotations

from pathlib import Path

DM_ROOT = Path(__file__).resolve().parents[1] / "dm"
GAME_LITERALS = ("brambletrek", "dnd5e")


def _py_files_under(path: Path) -> list[Path]:
    return [p for p in path.rglob("*.py") if p.is_file()]


def test_dm_core_has_no_game_id_branches():
    """Shared dm modules must not branch on game ids."""
    allowed_with_literals = {
        DM_ROOT / "graph.py",  # thin re-export only
        DM_ROOT / "brambletrek_bootstrap.py",  # compat shim
        DM_ROOT / "opening_scene.py",  # begin_session still has BT opening branch
    }
    offenders: list[str] = []
    for path in _py_files_under(DM_ROOT):
        if path in allowed_with_literals:
            continue
        if "nodes" in path.parts:
            text = path.read_text(encoding="utf-8")
            for lit in GAME_LITERALS:
                if f'"{lit}"' in text or f"'{lit}'" in text:
                    offenders.append(f"{path.relative_to(DM_ROOT)}: {lit}")
    assert not offenders, "Game literals in shared dm/: " + ", ".join(offenders)


def test_agent_nodes_live_under_games():
    dnd_agents = Path(__file__).resolve().parents[1] / "games" / "dnd5e" / "dm" / "agents"
    bt_agents = Path(__file__).resolve().parents[1] / "games" / "brambletrek" / "dm" / "agents"
    assert (dnd_agents / "nodes.py").is_file()
    assert (bt_agents / "nodes.py").is_file()
