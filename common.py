"""Shared helpers: paths, polite HTTP session with retries, CSV loading."""
from __future__ import annotations

import csv
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

YEARS = list(range(2016, 2025))  # 2016..2024 inclusive -> 9 time points


def load_companies() -> list[dict]:
    with open(CONFIG / "companies.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_seeds() -> dict[str, list[str]]:
    """ticker -> candidate URLs, ordered by priority (1 = preferred)."""
    seeds: dict[str, list[tuple[int, str]]] = {}
    with open(CONFIG / "about_url_seeds.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            seeds.setdefault(row["ticker"], []).append((int(row["priority"]), row["url"].strip()))
    return {t: [u for _, u in sorted(v)] for t, v in seeds.items()}


def make_session(user_agent: str) -> requests.Session:
    """Session that retries 429/5xx with exponential backoff (Wayback and EDGAR both throttle)."""
    s = requests.Session()
    retry = Retry(
        total=6,
        backoff_factor=2,  # 2, 4, 8, 16 ... seconds
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = user_agent
    return s


class RateLimiter:
    """Simple min-interval limiter so we stay polite to free public APIs."""

    def __init__(self, min_interval_s: float):
        self.min_interval_s = min_interval_s
        self._last = 0.0

    def wait(self) -> None:
        gap = time.monotonic() - self._last
        if gap < self.min_interval_s:
            time.sleep(self.min_interval_s - gap)
        self._last = time.monotonic()
