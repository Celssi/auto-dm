#!/usr/bin/env python3
"""Validate curated Brambletrek YAML (run from auto-dm repo root)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.games.brambletrek.curated_audit import structural_audit  # noqa: E402


def main() -> int:
    issues = structural_audit()
    if issues:
        print("validate_brambletrek_curated: structural issues:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests/test_brambletrek_curated.py", "-q"],
        cwd=ROOT,
    )
    if result.returncode == 0:
        print("validate_brambletrek_curated: OK")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
