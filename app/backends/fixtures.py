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

"""Fixture market data backend. The default, and what the tests run against.

No network, no rate limits, and the same numbers on every run — which is what
makes eval scores comparable across days. Selected with MARKET_DATA_BACKEND=fixtures.

The data below is a real yfinance snapshot taken 2026-08-30, not invented
figures, so the shapes and edge cases match what `live` actually returns:
NVDA carries the intraday-vs-last-close discrepancy the technical analyst is
instructed to reconcile, and INTC has null growth fields that must render as
'n/a'.

An unknown ticker returns a structured error rather than raising. That is
load-bearing: an analyst node that raises dies without emitting output, and
the JoinNode in the graph would then wait for it forever.

Regenerate with: uv run python scripts/refresh_fixtures.py
"""

# fmt: off

SNAPSHOT = {'NVDA': {'quote': {'ticker': 'NVDA',
                    'currency': 'USD',
                    'quote_type': 'live_or_delayed_intraday',
                    'price': 217.55,
                    'previous_close': 226.15,
                    'day_change_pct': -3.8,
                    'week52_high': 236.54,
                    'week52_low': 164.07,
                    'market_cap': 5253179850000.0},
          'history': {'ticker': 'NVDA',
                      'period': '1y',
                      'trading_days': 250,
                      'first_close': 173.95,
                      'first_close_date': '2025-08-29',
                      'last_close': 227.98,
                      'last_close_date': '2026-08-27',
                      'return_pct': 31.06,
                      'ma50': 208.16,
                      'ma200': 195.57,
                      'month_end_closes': {'2025-08-31': 173.95,
                                           '2025-09-30': 186.34,
                                           '2025-10-31': 202.23,
                                           '2025-11-30': 176.77,
                                           '2025-12-31': 186.27,
                                           '2026-01-31': 190.9,
                                           '2026-02-28': 176.97,
                                           '2026-03-31': 174.2,
                                           '2026-04-30': 199.34,
                                           '2026-05-31': 210.89,
                                           '2026-06-30': 200.09,
                                           '2026-07-31': 200.75,
                                           '2026-08-31': 227.98}},
          'fundamentals': {'ticker': 'NVDA',
                           'sector': 'Technology',
                           'industry': 'Semiconductors',
                           'marketCap': 5253179637760,
                           'trailingPE': 28.81457,
                           'forwardPE': 14.213399,
                           'priceToSalesTrailing12Months': 17.338943,
                           'enterpriseToEbitda': 25.933,
                           'profitMargins': 0.63663,
                           'grossMargins': 0.74674004,
                           'revenueGrowth': 1.059,
                           'earningsGrowth': 1.278,
                           'debtToEquity': 16.971,
                           'freeCashflow': 41809874944,
                           'returnOnEquity': 1.17211},
          'news': {'ticker': 'NVDA',
                   'articles': [{'title': "Wall Street is turning Nvidia's AI "
                                          'chips into a new futures market: Chart '
                                          'of the Day',
                                 'publisher': 'Yahoo Finance',
                                 'published': '2026-08-29T11:51:18Z',
                                 'summary': 'AI spending keeps getting bigger — '
                                            'figuring out how to price it is still '
                                            'hard.'},
                                {'title': 'President Trump Says the CFTC Is '
                                          'Working to Bring Hyperliquid to the '
                                          'United States. Does That Make It a '
                                          'Screaming Buy?',
                                 'publisher': 'Motley Fool',
                                 'published': '2026-08-30T01:50:00Z',
                                 'summary': 'Spoken words and implemented policies '
                                            'are not the same thing.'},
                                {'title': "If You'd Invested $1,000 in QQQ 20 "
                                          "Years Ago, Here's What You'd Have Today",
                                 'publisher': 'Motley Fool',
                                 'published': '2026-08-30T01:20:00Z',
                                 'summary': 'Your investment would have grown '
                                            'substantially, but only if you '
                                            'exercised discipline and patience.'},
                                {'title': "Peter Thiel's Fund Reported Zero Stocks "
                                          'for 2 Straight Quarters. Its $419 '
                                          'Million Comeback Put 72% Into Energy '
                                          'and Power.',
                                 'publisher': 'Motley Fool',
                                 'published': '2026-08-30T01:03:01Z',
                                 'summary': 'The fund reported nothing for six '
                                            'months. Its comeback filing lists one '
                                            'tech stock and seven energy bets.'},
                                {'title': 'Bitcoin Could Hit $300,000 by 2030, '
                                          'Says Coinbase CEO Brian Armstrong. '
                                          "Here's Why He's Right.",
                                 'publisher': 'Motley Fool',
                                 'published': '2026-08-30T00:20:00Z',
                                 'summary': 'If it is able to maintain its '
                                            'historical rate of growth, Bitcoin '
                                            'could triple in price by 2030.'}]}},
 'INTC': {'quote': {'ticker': 'INTC',
                    'currency': 'USD',
                    'quote_type': 'live_or_delayed_intraday',
                    'price': 89.47,
                    'previous_close': 91.13,
                    'day_change_pct': -1.82,
                    'week52_high': 142.35,
                    'week52_low': 23.68,
                    'market_cap': 472947837791.14},
          'history': {'ticker': 'INTC',
                      'period': '1y',
                      'trading_days': 250,
                      'first_close': 24.35,
                      'first_close_date': '2025-08-29',
                      'last_close': 92.09,
                      'last_close_date': '2026-08-27',
                      'return_pct': 278.19,
                      'ma50': 105.55,
                      'ma200': 72.53,
                      'month_end_closes': {'2025-08-31': 24.35,
                                           '2025-09-30': 33.55,
                                           '2025-10-31': 39.99,
                                           '2025-11-30': 40.56,
                                           '2025-12-31': 36.9,
                                           '2026-01-31': 46.47,
                                           '2026-02-28': 45.61,
                                           '2026-03-31': 44.13,
                                           '2026-04-30': 94.48,
                                           '2026-05-31': 114.68,
                                           '2026-06-30': 139.63,
                                           '2026-07-31': 90.2,
                                           '2026-08-31': 92.09}},
          'fundamentals': {'ticker': 'INTC',
                           'sector': 'Technology',
                           'industry': 'Semiconductors',
                           'marketCap': 472947818496,
                           'trailingPE': None,
                           'forwardPE': 43.855053,
                           'priceToSalesTrailing12Months': 8.292675,
                           'enterpriseToEbitda': 28.961,
                           'profitMargins': -0.19794,
                           'grossMargins': 0.38873002,
                           'revenueGrowth': 0.254,
                           'earningsGrowth': None,
                           'debtToEquity': 48.997,
                           'freeCashflow': 4866375168,
                           'returnOnEquity': -0.10715},
          'news': {'ticker': 'INTC',
                   'articles': [{'title': 'Intel vs. AMD: Why the Market Share '
                                          'Number Is Misleading',
                                 'publisher': 'Barchart',
                                 'published': '2026-08-29T18:30:02Z',
                                 'summary': 'AMD crossed 30% in client CPUs, yet '
                                            'its bigger win over Intel is in the '
                                            'data center that actually drives '
                                            'profits.'},
                                {'title': "I'd Rather Bet on AI's Electric Bill "
                                          "Than Its Chips. Here's Why.",
                                 'publisher': 'Motley Fool',
                                 'published': '2026-08-29T16:35:00Z',
                                 'summary': 'Technology changes fast, but '
                                            "electricity doesn't."},
                                {'title': 'Intel Sold Its NAND Memory Business for '
                                          'About $9 Billion. Micron Is Now Worth '
                                          'More Than Twice What Intel Is.',
                                 'publisher': 'Motley Fool',
                                 'published': '2026-08-29T09:07:01Z',
                                 'summary': 'The chipmaker exited NAND memory in '
                                            "one of the semiconductor industry's "
                                            'biggest asset sales. Nearly six years '
                                            'later, the market has put a price on '
                                            'what it walked away from.'},
                                {'title': 'This AI Energy Stock Is Up Nearly '
                                          '2,000% in the Last Two Years. Could It '
                                          "Be Nvidia's Next Big Investment?",
                                 'publisher': 'Motley Fool',
                                 'published': '2026-08-28T22:35:00Z',
                                 'summary': 'Nvidia just dropped $20 billion on '
                                            'SpaceX. Which company will be next?'},
                                {'title': 'Nvidia Quietly Became Its Own Market '
                                          'Category',
                                 'publisher': 'GuruFocus.com',
                                 'published': '2026-08-28T22:25:31Z',
                                 'summary': 'One striking market signal shows how '
                                            'much has changed'}]}},
 'F': {'quote': {'ticker': 'F',
                 'currency': 'USD',
                 'quote_type': 'live_or_delayed_intraday',
                 'price': 13.88,
                 'previous_close': 13.97,
                 'day_change_pct': -0.64,
                 'week52_high': 17.78,
                 'week52_low': 11.11,
                 'market_cap': 55347827857.96001},
       'history': {'ticker': 'F',
                   'period': '1y',
                   'trading_days': 250,
                   'first_close': 11.25,
                   'first_close_date': '2025-08-29',
                   'last_close': 13.95,
                   'last_close_date': '2026-08-27',
                   'return_pct': 24.05,
                   'ma50': 13.99,
                   'ma200': 13.19,
                   'month_end_closes': {'2025-08-31': 11.25,
                                        '2025-09-30': 11.43,
                                        '2025-10-31': 12.55,
                                        '2025-11-30': 12.84,
                                        '2025-12-31': 12.68,
                                        '2026-01-31': 13.42,
                                        '2026-02-28': 13.77,
                                        '2026-03-31': 11.27,
                                        '2026-04-30': 11.8,
                                        '2026-05-31': 17.25,
                                        '2026-06-30': 13.75,
                                        '2026-07-31': 14.52,
                                        '2026-08-31': 13.95}},
       'fundamentals': {'ticker': 'F',
                        'sector': 'Consumer Cyclical',
                        'industry': 'Auto Manufacturers',
                        'marketCap': 55347830784,
                        'trailingPE': None,
                        'forwardPE': 7.254482,
                        'priceToSalesTrailing12Months': 0.29444566,
                        'enterpriseToEbitda': 25.718,
                        'profitMargins': -0.03935,
                        'grossMargins': 0.07115,
                        'revenueGrowth': -0.038,
                        'earningsGrowth': None,
                        'debtToEquity': 456.708,
                        'freeCashflow': -7940250112,
                        'returnOnEquity': -0.18252},
       'news': {'ticker': 'F',
                'articles': [{'title': "NIO's Next Earnings Report on September 1 "
                                       "Could Send the Stock Soaring. Here's Why.",
                              'publisher': 'Motley Fool',
                              'published': '2026-08-29T22:50:01Z',
                              'summary': 'This could be the moment Nio investors '
                                         'have been waiting years for.'},
                             {'title': 'History Says What Ford Stock Has Done in '
                                       'the 2 Years After Each Full-Year Loss',
                              'publisher': 'Motley Fool',
                              'published': '2026-08-28T23:43:01Z',
                              'summary': 'Seven other full-year losses this '
                                         'century were followed by everything from '
                                         'a 70% wipeout to a 633% gain.'},
                             {'title': 'Ford (F) and General Motors (GM) Battle '
                                       'for Title of Most “American-Made” '
                                       'Automaker',
                              'publisher': 'Insider Monkey',
                              'published': '2026-08-28T15:14:29Z',
                              'summary': 'On August 15, 2026, the Wall Street '
                                         'Journal reported that Ford Motor Company '
                                         '(NYSE:F) and General Motors Company '
                                         '(NYSE:GM) are privately lobbying for '
                                         'tariff policies that favor their own '
                                         'manufacturing footprints while each '
                                         'publicly claims to be the more '
                                         '“American” automaker. Ford, which builds '
                                         'about 80% of its U.S. sold vehicles '
                                         'domestically and employs more […]'},
                             {'title': 'Ford names new president of subsidiary '
                                       'Ford Energy',
                              'publisher': 'Wards Auto',
                              'published': '2026-08-28T14:27:00Z',
                              'summary': 'Dave Carroll takes over from company '
                                         'veteran Lisa Drake, who is retiring from '
                                         'the automaker after a 32-year career.'},
                             {'title': 'Zacks Industry Outlook General Motors, '
                                       'PACCAR, Ford and Harley-Davidson',
                              'publisher': 'Zacks',
                              'published': '2026-08-28T07:06:00Z',
                              'summary': 'General Motors, PACCAR, Ford and '
                                         'Harley-Davidson have been highlighted in '
                                         'this Industry Outlook article.'}]}}}

# fmt: on

AVAILABLE_TICKERS = sorted(SNAPSHOT)


def _lookup(ticker: str, section: str) -> dict:
    """Return one section for a ticker, or a structured error if it is unknown."""
    data = SNAPSHOT.get(ticker.upper())
    if data is None:
        return {
            "ticker": ticker.upper(),
            "error": (
                f"No fixture data for {ticker.upper()}. Available tickers: "
                f"{', '.join(AVAILABLE_TICKERS)}. Set MARKET_DATA_BACKEND=live "
                f"to query the market directly."
            ),
        }
    return data[section]


def get_quote(ticker: str) -> dict:
    """Latest intraday price, day move, and 52-week range."""
    return _lookup(ticker, "quote")


def get_history(ticker: str, period: str = "1y") -> dict:
    """Price history with trend context. Fixtures only cover period='1y'."""
    result = _lookup(ticker, "history")
    if "error" in result or period == result.get("period"):
        return result
    return {
        **result,
        "requested_period": period,
        "note": (
            f"Fixture data only covers period='{result['period']}'; "
            f"'{period}' was requested. Figures below are for "
            f"'{result['period']}'."
        ),
    }


def get_fundamentals(ticker: str) -> dict:
    """Valuation multiples, margins, growth rates, and leverage."""
    return _lookup(ticker, "fundamentals")


def get_news(ticker: str) -> dict:
    """Recent news headlines."""
    return _lookup(ticker, "news")
