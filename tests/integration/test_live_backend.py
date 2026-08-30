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

"""Live backend tests: these actually call yfinance.

Kept out of tests/unit so the unit suite stays offline and deterministic. These
assert shapes and invariants, never specific prices — the values move daily.

If Yahoo rate-limits or changes its payload, these are the tests that catch it
before a run with MARKET_DATA_BACKEND=live does.
"""

import pytest

from app.backends import fixtures, live

TICKER = "NVDA"


def test_live_quote_has_the_shape_the_fixtures_promise() -> None:
    """Fixtures are a snapshot of this; a drift here makes them a lie."""
    quote = live.get_quote(TICKER)
    assert "error" not in quote, quote.get("error")
    assert set(quote) == set(fixtures.get_quote(TICKER))
    assert quote["price"] > 0
    assert quote["week52_low"] <= quote["week52_high"]


def test_live_history_has_the_shape_the_fixtures_promise() -> None:
    history = live.get_history(TICKER, "1y")
    assert "error" not in history, history.get("error")
    assert set(history) == set(fixtures.get_history(TICKER, "1y"))
    assert history["trading_days"] > 200
    assert history["month_end_closes"]


def test_live_history_never_returns_a_nan_close() -> None:
    """The in-progress session's NaN bar must be dropped, not passed through."""
    history = live.get_history(TICKER, "1y")
    assert history["last_close"] is not None
    assert history["last_close_date"]
    assert all(v is not None for v in history["month_end_closes"].values())


def test_live_fundamentals_have_the_shape_the_fixtures_promise() -> None:
    fundamentals = live.get_fundamentals(TICKER)
    assert "error" not in fundamentals, fundamentals.get("error")
    assert set(fundamentals) == set(fixtures.get_fundamentals(TICKER))


def test_live_news_returns_dated_articles() -> None:
    news = live.get_news(TICKER)
    assert "error" not in news, news.get("error")
    assert news["articles"]
    assert any(a["title"] and a["published"] for a in news["articles"])


@pytest.mark.parametrize(
    "tool",
    [live.get_quote, live.get_fundamentals, live.get_history],
    ids=["quote", "fundamentals", "history"],
)
def test_live_tools_return_an_error_for_a_nonsense_symbol(tool) -> None:
    """Must degrade to a structured error, or the JoinNode stalls on a dead node.

    Yahoo signals an unknown symbol inconsistently — None prices here, a raised
    KeyError there — so each tool is checked rather than assumed.
    """
    result = tool("ZZZZQQQQ")
    assert "error" in result
