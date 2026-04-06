import json
import re
from statistics import mean
from typing import List, Optional
from urllib.parse import quote_plus

import requests


PRICE_PATTERN = re.compile(r"\$?\b(\d+(?:[.,]\d{1,2})?)\s?(?:usd|vnd|d|đ)?\b", re.IGNORECASE)
TITLE_PATTERN_DDG = re.compile(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
SNIPPET_PATTERN_DDG = re.compile(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
URL_PATTERN_DDG = re.compile(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"', re.IGNORECASE)
TAG_PATTERN = re.compile(r"<[^>]+>")


def _extract_prices(text: str) -> List[float]:
    prices: List[float] = []
    for raw in PRICE_PATTERN.findall(text or ""):
        try:
            prices.append(float(raw.replace(",", ".")))
        except ValueError:
            continue
    return prices


def _clean_html(raw: str) -> str:
    text = TAG_PATTERN.sub(" ", raw or "")
    return re.sub(r"\s+", " ", text).strip()


def _search_duckduckgo_html(query: str, limit: int = 8) -> List[dict]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=15,
    )
    response.raise_for_status()

    html = response.text
    titles = TITLE_PATTERN_DDG.findall(html)
    snippets = SNIPPET_PATTERN_DDG.findall(html)
    urls = URL_PATTERN_DDG.findall(html)

    results = []
    for idx in range(min(limit, len(titles), len(urls))):
        title = _clean_html(titles[idx])
        snippet = _clean_html(snippets[idx]) if idx < len(snippets) else ""
        href = urls[idx]
        results.append({"title": title, "body": snippet, "href": href})
    return results


def search_web_travel_price(query: str, location: Optional[str] = None) -> str:
    if not query or not query.strip():
        raise ValueError("query cannot be empty")

    full_query = query.strip()
    if location and location.strip():
        full_query = f"{full_query} {location.strip()}"

    all_prices: List[float] = []
    sources = []

    results = _search_duckduckgo_html(full_query, limit=8)
    for item in results:
        title = item.get("title", "")
        body = item.get("body", "")
        href = item.get("href", "")
        all_prices.extend(_extract_prices(f"{title} {body}"))
        sources.append({"title": title, "url": href})

    average_price = round(mean(all_prices), 2) if all_prices else None
    return json.dumps(
        {
            "query": full_query,
            "average_price_signal": average_price,
            "prices_found_count": len(all_prices),
            "sources": sources[:5],
        },
        ensure_ascii=False,
    )
