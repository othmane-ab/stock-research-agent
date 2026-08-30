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

"""The four market data tools exposed to the model.

This module is the schema layer: the docstrings and type hints below are what
the model actually sees when deciding how to call these, so they are
load-bearing, not decoration. The data itself comes from whichever backend
MARKET_DATA_BACKEND selects — see `app.backends`.

Any of these can return a dict with an `error` key instead of data (unknown
ticker, no history). That is deliberate rather than an exception: an analyst
node that raises dies without emitting output, and the JoinNode in the graph
would wait for it forever. The analysts are instructed to report the gap.
"""

from .backends import active_backend


def get_quote(ticker: str) -> dict:
    """Get the latest price, day move, and 52-week range for a stock.

    Args:
        ticker: Stock symbol, for example "NVDA".

    Returns:
        Live (possibly delayed) price, previous close, percent day change,
        52-week range, and market cap. This is an intraday quote and may
        differ from the last completed daily close reported by `get_history`.
        Returns an `error` key instead if the symbol is unknown.
    """
    return active_backend().get_quote(ticker)


def get_history(ticker: str, period: str = "1y") -> dict:
    """Get price history with trend context: return, moving averages, range.

    Args:
        ticker: Stock symbol, for example "NVDA".
        period: Lookback window, one of "1mo", "3mo", "6mo", "1y", "2y", "5y".

    Returns:
        Start and end closes with their dates, percent return over the window,
        50- and 200-day moving averages, and month-end closes. `last_close` is
        the last *completed* daily session and may differ from the intraday
        price from `get_quote`. Returns an `error` key instead if the symbol
        is unknown or has no price history.
    """
    return active_backend().get_history(ticker, period)


def get_fundamentals(ticker: str) -> dict:
    """Get valuation multiples, margins, growth rates, and leverage for a stock.

    Args:
        ticker: Stock symbol, for example "NVDA".

    Returns:
        Sector and industry plus valuation, profitability, growth, and balance
        sheet metrics. Margins and growth are decimal fractions, so 0.63663
        means 63.7%. Metrics the issuer does not publish come back as null.
        Returns an `error` key instead if the symbol is unknown.
    """
    return active_backend().get_fundamentals(ticker)


def get_news(ticker: str) -> dict:
    """Get recent news headlines for a stock.

    Args:
        ticker: Stock symbol, for example "NVDA".

    Returns:
        Recent articles with title, publisher, publish date, and summary.
        Returns an `error` key instead if the symbol is unknown.
    """
    return active_backend().get_news(ticker)
