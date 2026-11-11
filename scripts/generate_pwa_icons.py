#!/usr/bin/env python3
"""Deprecated: icons now come from assets/brand/hedgehog-source.png.

Run:  python3 scripts/generate-icons.py
"""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('generate-icons.py')), run_name='__main__')
