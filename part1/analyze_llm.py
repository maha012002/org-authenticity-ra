"""Compatibility entry point — theme coding is dictionary/lexicon-based (see code_themes.py).

Usage:  python part1/analyze_llm.py [--tickers MSFT JNJ] [--force]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from code_themes import main  # noqa: E402

if __name__ == "__main__":
    main()
