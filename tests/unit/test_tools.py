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

"""Unit tests for the market data tools and the agent graph wiring.

No network: these run against the fixtures backend, which is the default.
The live backend's yfinance calls are exercised by tests/integration/.
"""

import math
from typing import ClassVar

import pandas as pd
import pytest
from google.adk.workflow import START

from app import backends, tools
from app.agent import (
    fundamentals_analyst,
    gather,
    news_analyst,
    report_writer,
    root_agent,
    technical_analyst,
)
from app.backends import fixtures, live

TOOLS = (tools.get_quote, tools.get_history, tools.get_fundamentals, tools.get_news)


# --------------------------------------------------------------------------
# Backend selection
# --------------------------------------------------------------------------


def test_fixtures_is_the_default_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deterministic data by default, so eval scores stay comparable across days."""
    monkeypatch.delenv("MARKET_DATA_BACKEND", raising=False)
    assert backends.active_backend() is fixtures


def test_backend_is_selected_per_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolved per call, not cached at import, or tests could not flip it."""
    monkeypatch.setenv("MARKET_DATA_BACKEND", "live")
    assert backends.active_backend() is live
    monkeypatch.setenv("MARKET_DATA_BACKEND", "FIXTURES")
    assert backends.active_backend() is fixtures


def test_unknown_backend_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    """A typo must not silently fall back to a different data source."""
    monkeypatch.setenv("MARKET_DATA_BACKEND", "yahoo")
    with pytest.raises(ValueError, match="Unknown MARKET_DATA_BACKEND"):
        backends.active_backend()


def test_both_backends_expose_the_same_callables() -> None:
    """`app.tools` dispatches blindly, so the two must stay interchangeable."""
    for name in ("get_quote", "get_history", "get_fundamentals", "get_news"):
        assert callable(getattr(fixtures, name))
        assert callable(getattr(live, name))


# --------------------------------------------------------------------------
# Unknown tickers must return output, never raise
# --------------------------------------------------------------------------


@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t.__name__)
def test_unknown_ticker_returns_error_instead_of_raising(tool) -> None:
    """An analyst that raises dies without emitting, and the JoinNode hangs forever.

    So every tool must come back with a structured error the analyst can report.
    """
    result = tool("ZZZZ")
    assert "error" in result
    assert "ZZZZ" in result["error"]


def test_unknown_ticker_error_names_the_available_tickers() -> None:
    """The model should be able to tell the user what it *can* research."""
    error = fixtures.get_quote("ZZZZ")["error"]
    for ticker in fixtures.AVAILABLE_TICKERS:
        assert ticker in error


def test_live_quote_survives_a_delisted_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    """yfinance returns None prices for delisted symbols; arithmetic on that raises."""

    class DeadTicker:
        class fast_info:
            last_price = None
            previous_close = None
            currency = "USD"
            market_cap = None
            year_high = None
            year_low = None

    monkeypatch.setattr(live.yf, "Ticker", lambda ticker: DeadTicker())
    result = live.get_quote("SKYT")
    assert "error" in result
    assert "delisted" in result["error"]


def test_live_quote_survives_an_unknown_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    """Yahoo's other failure mode: fast_info raises while lazy-loading metadata."""

    class RaisingFastInfo:
        def __getattr__(self, name: str):
            raise KeyError("currentTradingPeriod")

    class UnknownTicker:
        fast_info = RaisingFastInfo()

    monkeypatch.setattr(live.yf, "Ticker", lambda ticker: UnknownTicker())
    result = live.get_quote("ZZZZQQQQ")
    assert "error" in result
    assert "unknown symbol" in result["error"]


def test_live_history_survives_an_empty_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty series would make iloc[0] raise IndexError."""

    class EmptyTicker:
        def history(self, period: str) -> pd.DataFrame:
            return pd.DataFrame({"Close": []}, index=pd.to_datetime([]))

    monkeypatch.setattr(live.yf, "Ticker", lambda ticker: EmptyTicker())
    assert "error" in live.get_history("SKYT", "1y")


# --------------------------------------------------------------------------
# Live backend shaping logic
# --------------------------------------------------------------------------


def test_round_maps_nan_and_none_to_none() -> None:
    """NaN must become None so the model renders 'n/a' rather than a bogus number."""
    assert live._round(float("nan")) is None
    assert live._round(None) is None
    assert live._round(1.23456) == 1.23
    assert live._round(1.23456, 4) == 1.2346


def _frame_with_partial_bar() -> pd.DataFrame:
    """Four sessions where the most recent is still in progress (NaN close)."""
    index = pd.to_datetime(["2026-08-25", "2026-08-26", "2026-08-27", "2026-08-28"])
    return pd.DataFrame({"Close": [100.0, 110.0, 120.0, math.nan]}, index=index)


def test_closes_drops_partial_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    """yfinance emits a NaN Close for the in-progress session; it must be dropped.

    Without this, `close.iloc[-1]` is NaN and every downstream figure —
    last_close, return_pct, both moving averages — silently becomes null.
    """
    frame = _frame_with_partial_bar()

    class FakeTicker:
        def history(self, period: str) -> pd.DataFrame:
            return frame

    monkeypatch.setattr(live.yf, "Ticker", lambda ticker: FakeTicker())

    close = live._closes("TEST", "1y")
    assert len(close) == 3
    assert close.iloc[-1] == 120.0


def test_get_history_reports_dates_for_both_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """last_close must carry its date so the writer can reconcile it with get_quote."""
    frame = _frame_with_partial_bar()

    class FakeTicker:
        def history(self, period: str) -> pd.DataFrame:
            return frame

    monkeypatch.setattr(live.yf, "Ticker", lambda ticker: FakeTicker())

    result = live.get_history("test", "1y")
    assert result["ticker"] == "TEST"
    assert result["last_close"] == 120.0
    assert result["last_close_date"] == "2026-08-27"
    assert result["first_close_date"] == "2026-08-25"
    assert result["return_pct"] == 20.0
    # Fewer than 50 rows, so the moving averages are unavailable, not fabricated.
    assert result["ma50"] is None
    assert result["ma200"] is None


def test_get_news_tolerates_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Yahoo articles vary in shape; a missing provider must not raise."""

    class FakeTicker:
        news: ClassVar[list[dict]] = [
            {"content": {"title": "A", "provider": {"displayName": "Reuters"}}},
            {"content": {"title": "B", "description": "fallback summary"}},
            {},
        ]

    monkeypatch.setattr(live.yf, "Ticker", lambda ticker: FakeTicker())

    articles = live.get_news("test")["articles"]
    assert [a["title"] for a in articles] == ["A", "B", None]
    assert articles[0]["publisher"] == "Reuters"
    assert articles[1]["publisher"] is None
    assert articles[1]["summary"] == "fallback summary"


# --------------------------------------------------------------------------
# Fixture data quality
# --------------------------------------------------------------------------


def test_fixtures_carry_every_section_for_every_ticker() -> None:
    """A missing section would surface as a KeyError mid-run."""
    for ticker in fixtures.AVAILABLE_TICKERS:
        assert set(fixtures.SNAPSHOT[ticker]) == {
            "quote",
            "history",
            "fundamentals",
            "news",
        }
        assert fixtures.get_news(ticker)["articles"]
        assert fixtures.get_quote(ticker)["price"] is not None


def test_fixtures_preserve_the_intraday_vs_close_discrepancy() -> None:
    """The NVDA snapshot is the case technical_analyst is told to reconcile.

    If a refresh ever flattens this, the reconciliation instruction stops
    being exercised by the eval set.
    """
    quote = fixtures.get_quote("NVDA")
    history = fixtures.get_history("NVDA")
    gap_pct = abs(quote["price"] - history["last_close"]) / history["last_close"] * 100
    assert gap_pct > 1.0
    assert history["last_close_date"]


def test_fixture_history_flags_an_unsupported_period() -> None:
    """The model must not read 1y figures as though they covered 5y."""
    result = fixtures.get_history("NVDA", "5y")
    assert result["requested_period"] == "5y"
    assert "1y" in result["note"]
    # The underlying figures are still the 1y ones, and still labelled as such.
    assert result["period"] == "1y"


# --------------------------------------------------------------------------
# Graph wiring
# --------------------------------------------------------------------------


def test_writer_reads_exactly_the_keys_the_analysts_write() -> None:
    """A typo on either side yields a silently empty memo section."""
    analysts = (fundamentals_analyst, technical_analyst, news_analyst)
    written = {agent.output_key for agent in analysts}
    assert written == {"fundamentals", "technicals", "news"}

    # `instruction` also accepts a callable provider; this one is a plain string.
    instruction = report_writer.instruction
    assert isinstance(instruction, str)
    for key in written:
        assert f"{{{key}}}" in instruction


def test_analysts_fan_out_from_start_and_join_before_the_writer() -> None:
    """All three analysts must reach `gather`, or the memo loses a section."""
    analysts = (fundamentals_analyst, technical_analyst, news_analyst)

    for analyst in analysts:
        assert (START, analyst, gather) in root_agent.edges

    assert (gather, report_writer) in root_agent.edges


def test_fixtures_mode_drops_the_live_web_search() -> None:
    """`google_search` is a live call and would reintroduce nondeterminism.

    The tests run under the default fixtures backend, so the news analyst must
    be offline here. Its tool list is fixed at import, unlike the data backend.
    """
    tool_names = {
        getattr(t, "__name__", getattr(t, "name", "")) for t in news_analyst.tools
    }
    assert tool_names == {"get_news"}

    instruction = news_analyst.instruction
    assert isinstance(instruction, str)
    assert "google_search" not in instruction


def test_analysts_retry_so_the_join_node_cannot_stall() -> None:
    """A predecessor that dies without emitting output leaves the JoinNode waiting."""
    for analyst in (fundamentals_analyst, technical_analyst, news_analyst):
        retry_config = analyst.retry_config
        assert retry_config is not None
        assert retry_config.max_attempts is not None
        assert retry_config.max_attempts >= 2
