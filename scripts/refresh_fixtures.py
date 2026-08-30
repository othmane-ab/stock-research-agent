# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Re-snapshot live market data into app/backends/fixtures.py.

    uv run python scripts/refresh_fixtures.py [TICKER ...]

Rewrites only the SNAPSHOT literal, leaving the module's lookup functions
intact. Expect eval scores to shift after a refresh — the agent's inputs
changed, so compare against a fresh baseline rather than the old one.
"""

import pprint
import re
import sys
from pathlib import Path

from app.backends import live

DEFAULT_TICKERS = ("NVDA", "INTC", "F")
FIXTURES = Path(__file__).resolve().parent.parent / "app" / "backends" / "fixtures.py"
MAX_ARTICLES = 5


def snapshot(tickers: tuple[str, ...]) -> dict:
    """Pull every section for each ticker from the live backend."""
    out = {}
    for ticker in tickers:
        quote = live.get_quote(ticker)
        if "error" in quote:
            print(f"  {ticker}: skipped — {quote['error']}")
            continue
        out[ticker.upper()] = {
            "quote": quote,
            "history": live.get_history(ticker, "1y"),
            "fundamentals": live.get_fundamentals(ticker),
            "news": {
                "ticker": ticker.upper(),
                "articles": live.get_news(ticker)["articles"][:MAX_ARTICLES],
            },
        }
        print(f"  {ticker}: ok — price={quote['price']}")
    return out


def main() -> int:
    tickers = tuple(sys.argv[1:]) or DEFAULT_TICKERS
    print(f"Snapshotting {', '.join(tickers)} from the live backend...")
    data = snapshot(tickers)
    if not data:
        print("No tickers returned data; fixtures left unchanged.", file=sys.stderr)
        return 1

    literal = "SNAPSHOT = " + pprint.pformat(data, width=84, sort_dicts=False) + "\n"
    source = FIXTURES.read_text()
    updated, count = re.subn(
        r"^SNAPSHOT = \{.*?^\}\n",
        literal,
        source,
        count=1,
        flags=re.DOTALL | re.MULTILINE,
    )
    if count != 1:
        print("Could not locate the SNAPSHOT literal to replace.", file=sys.stderr)
        return 1

    FIXTURES.write_text(updated)
    print(f"Wrote {len(data)} tickers to {FIXTURES.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
