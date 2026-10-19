"""Part 1, step 2: turn archived HTML into clean visible body text.

Method:
  1. Remove the Wayback toolbar/banner (present on redirect-followed pages).
  2. Primary extractor: trafilatura (boilerplate removal tuned for main content).
  3. Fallback: BeautifulSoup -- drop <script>, <style>, <nav>, <header>, <footer>,
     <aside>, <form>, cookie/consent banners, then keep visible text.
     Used when trafilatura returns < MIN_CHARS (common on JS-heavy or very short pages).
  4. Normalise whitespace and drop lines that repeat across many companies' pages
     (e.g. "Skip to main content") -- see BOILERPLATE_LINES.

Output:
  data/part1/text/<ticker>_<year>.txt
  data/part1/extraction_log.csv  (method used, character counts) -> lets you audit quality
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA  # noqa: E402

try:
    import trafilatura
except ImportError:  # extraction still works, just with the fallback only
    trafilatura = None

HTML_DIR = DATA / "part1" / "html"
TEXT_DIR = DATA / "part1" / "text"
LOG = DATA / "part1" / "extraction_log.csv"
TEXT_DIR.mkdir(parents=True, exist_ok=True)

MIN_CHARS = 300
WAYBACK_TOOLBAR = re.compile(r"<!-- BEGIN WAYBACK TOOLBAR INSERT -->.*?<!-- END WAYBACK TOOLBAR INSERT -->", re.S)
NOISE_SELECTORS = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "iframe"]
NOISE_ATTR = re.compile(r"cookie|consent|banner|breadcrumb|menu|navbar|footer|header|skip|social|share", re.I)
BOILERPLATE_LINES = {
    "skip to main content", "skip to content", "menu", "search", "close", "back to top",
    "accept", "accept all cookies", "cookie settings", "share", "print",
}


def clean_lines(text: str) -> str:
    out = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 2 or line.lower() in BOILERPLATE_LINES:
            continue
        out.append(line)
    # de-duplicate consecutive repeats (mega-menus often repeat)
    deduped = [l for i, l in enumerate(out) if i == 0 or l != out[i - 1]]
    return "\n".join(deduped)


def bs4_extract(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(NOISE_SELECTORS):
        tag.decompose()
    for tag in soup.find_all(True):
        if tag.attrs is None:
            continue
        ident = " ".join([tag.get("id") or "", " ".join(tag.get("class") or []), tag.get("role") or ""])
        if NOISE_ATTR.search(ident) and tag.name not in ("body", "main", "html"):
            tag.decompose()
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body or soup
    return main.get_text("\n")


def extract(html: str) -> tuple[str, str]:
    html = WAYBACK_TOOLBAR.sub("", html)
    if trafilatura is not None:
        txt = trafilatura.extract(html, include_comments=False, include_tables=True, favor_recall=True) or ""
        txt = clean_lines(txt)
        if len(txt) >= MIN_CHARS:
            return txt, "trafilatura"
    txt = clean_lines(bs4_extract(html))
    return txt, "bs4_fallback"


def main() -> None:
    rows = []
    for path in sorted(HTML_DIR.glob("*.html")):
        stem = path.stem  # e.g. BRK-B_2019
        html = path.read_text(encoding="utf-8", errors="replace")
        text, method = extract(html)
        (TEXT_DIR / f"{stem}.txt").write_text(text, encoding="utf-8")
        flag = "short" if len(text) < MIN_CHARS else ""
        rows.append({"file": stem, "method": method, "html_chars": len(html), "text_chars": len(text), "flag": flag})
        print(f"{stem}: {method}, {len(text)} chars {flag}")
    with open(LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "method", "html_chars", "text_chars", "flag"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} files. Short extractions (<{MIN_CHARS} chars) flagged in {LOG} for manual review.")


if __name__ == "__main__":
    main()
