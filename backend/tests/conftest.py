"""Pytest hooks — disable LangSmith during automated tests."""

from __future__ import annotations

import os

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"