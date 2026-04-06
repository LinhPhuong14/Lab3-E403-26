import json
import re
from statistics import mean
from typing import List, Optional


PRICE_PATTERN = re.compile(r"\$?\b(\d+(?:[.,]\d{1,2})?)\s?(?:usd|vnd|d|đ)?\b", re.IGNORECASE)


def _extract_prices(text: str) -> List[float]:
    prices: List[float] = []
    for raw in PRICE_PATTERN.findall(text or ""):
        try:
            prices.append(float(raw.replace(",", ".")))
        except ValueError:
            continue
    return prices


def search_web_travel_price(query: str, location: Optional[str] = None) -> str:
    if not query or not query.strip():
        raise ValueError("query cannot be empty")

    try:
        from duckduckgo_search import DDGS
    except ImportError as exc:
        raise RuntimeError("duckduckgo_search is not installed. Run pip3 install -r requirements.txt") from exc

    full_query = query.strip()
    if location and location.strip():
        full_query = f"{full_query} {location.strip()}"

    all_prices: List[float] = []
    sources = []

    with DDGS() as ddgs:
        results = ddgs.text(full_query, max_results=8)
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
        ensure_ascii=True,
    )
