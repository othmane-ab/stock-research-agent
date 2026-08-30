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

"""Live market data backend, backed by yfinance.

Selected with MARKET_DATA_BACKEND=live. Returns real data at the cost of
network calls, rate limits, and figures that change under you between runs —
which is why `fixtures` is the default.

Deliberately no broad `except Exception` around the yfinance calls: ADK 2.x
retries failed tool calls automatically, and swallowing the exception here
would defeat that (see the 1.x->2.0 notes in docs/adk/README.md). The one
thing that IS caught is an unknown or delisted ticker — a permanent condition
no retry can fix, and one that must return output rather than raise, or the
JoinNode in the graph waits forever for an analyst that died.
"""

import math

import yfinance as yf

_FUNDAMENTAL_FIELDS = (
    "sector",
    "industry",
    "marketCap",
    "trailingPE",
    "forwardPE",
    "priceToSalesTrailing12Months",
    "enterpriseToEbitda",
    "profitMargins",
    "grossMargins",
    "revenueGrowth",
    "earningsGrowth",
    "debtToEquity",
    "freeCashflow",
    "returnOnEquity",
)


def _round(value: float | None, digits: int = 2) -> float | None:
    """Round a value, mapping NaN and None to None so the model sees 'n/a'."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def _no_data(ticker: str, detail: str) -> dict:
    """Structured 'no data' result. Never raise this — see the module docstring."""
    return {
        "ticker": ticker.upper(),
        "error": f"No market data available for {ticker.upper()}: {detail}.",
    }


def _closes(ticker: str, period: str):
    """Return the Close series for a ticker with empty/partial bars dropped.

    yfinance emits a NaN Close for the in-progress session, so without the
    dropna() every derived figure below silently becomes null.
    """
    return yf.Ticker(ticker).history(period=period)["Close"].dropna()


def get_quote(ticker: str) -> dict:
    """Latest intraday price, day move, and 52-week range.

    Yahoo has two distinct ways of not knowing a symbol, and both must degrade
    to a structured error rather than propagate: a delisted-but-known symbol
    yields None prices, while an entirely unknown one makes `fast_info` raise
    KeyError as it fails to lazy-load trading metadata. The KeyError catch is
    kept tight around that lookup so genuine transport failures still reach
    ADK's retry machinery.
    """
    info = yf.Ticker(ticker).fast_info
    try:
        last, prev = info.last_price, info.previous_close
        currency, market_cap = info.currency, info.market_cap
        year_high, year_low = info.year_high, info.year_low
    except KeyError:
        return _no_data(ticker, "unknown symbol")

    if last is None or prev is None:
        return _no_data(ticker, "unknown or delisted symbol")

    return {
        "ticker": ticker.upper(),
        "currency": currency,
        "quote_type": "live_or_delayed_intraday",
        "price": _round(last),
        "previous_close": _round(prev),
        "day_change_pct": _round((last - prev) / prev * 100),
        "week52_high": _round(year_high),
        "week52_low": _round(year_low),
        "market_cap": market_cap,
    }


def get_history(ticker: str, period: str = "1y") -> dict:
    """Price history with trend context: return, moving averages, month-end closes."""
    close = _closes(ticker, period)
    if close.empty:
        return _no_data(ticker, f"no price history for period '{period}'")

    first, last = close.iloc[0], close.iloc[-1]
    ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
    ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
    return {
        "ticker": ticker.upper(),
        "period": period,
        "trading_days": len(close),
        "first_close": _round(first),
        "first_close_date": str(close.index[0].date()),
        "last_close": _round(last),
        "last_close_date": str(close.index[-1].date()),
        "return_pct": _round((last / first - 1) * 100),
        "ma50": _round(ma50),
        "ma200": _round(ma200),
        "month_end_closes": {
            str(date.date()): _round(value)
            for date, value in close.resample("ME").last().dropna().items()
        },
    }


def get_fundamentals(ticker: str) -> dict:
    """Valuation multiples, margins, growth rates, and leverage."""
    info = yf.Ticker(ticker).info
    if not info or info.get("marketCap") is None:
        return _no_data(ticker, "no fundamentals published for this symbol")
    return {
        "ticker": ticker.upper(),
        **{field: info.get(field) for field in _FUNDAMENTAL_FIELDS},
    }


def get_news(ticker: str) -> dict:
    """Recent news headlines."""
    articles = []
    for item in yf.Ticker(ticker).news[:8]:
        content = item.get("content") or {}
        articles.append(
            {
                "title": content.get("title"),
                "publisher": (content.get("provider") or {}).get("displayName"),
                "published": content.get("pubDate"),
                "summary": content.get("summary") or content.get("description"),
            }
        )
    return {"ticker": ticker.upper(), "articles": articles}
