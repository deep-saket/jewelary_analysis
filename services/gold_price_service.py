import json
import re
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

GOODRETURNS_GOLD_RATE_URL = "https://www.goodreturns.in/gold-rates/"


class GoldPriceServiceError(RuntimeError):
    pass


def _extract_rate(text: str, karat: str) -> int:
    pattern = rf"{karat}\s*Gold\s*/g\s*₹\s*([\d,]+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        raise GoldPriceServiceError(f"Could not extract {karat} gold price from Goodreturns page.")
    return int(match.group(1).replace(",", ""))


def _extract_effective_date(text: str) -> str | None:
    match = re.search(r"Gold Price in India\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", text)
    return match.group(1) if match else None


def get_live_gold_rates() -> dict[str, Any]:
    response = requests.get(
        GOODRETURNS_GOLD_RATE_URL,
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0 (compatible; JewelleryValuationBot/1.0)"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    return {
        "source": "Goodreturns",
        "source_url": GOODRETURNS_GOLD_RATE_URL,
        "effective_date": _extract_effective_date(text),
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "unit": "INR per gram",
        "rates": {
            "24k": _extract_rate(text, "24K"),
            "22k": _extract_rate(text, "22K"),
            "18k": _extract_rate(text, "18K"),
        },
        "notes": [
            "Indicative rates scraped from Goodreturns.",
            "Rates may exclude GST, TCS, and other levies.",
        ],
    }


def format_gold_rate_context(gold_rates: dict[str, Any]) -> str:
    return json.dumps(gold_rates, indent=2)
