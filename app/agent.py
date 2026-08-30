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

"""Collaborative equity research agent: three analysts fan out, a writer synthesizes.

    START ->  fundamentals_analyst  -> state["fundamentals"]  -.
    START ->  technical_analyst     -> state["technicals"]     :-> gather -> report_writer
    START ->  news_analyst          -> state["news"]          -'

The three analysts run concurrently off START and re-join at a `JoinNode`,
which waits for all of them before `report_writer` runs.

The analysts never see each other's work; they communicate only by writing to
distinct session-state keys via `output_key`, which `report_writer` reads back
by name in its instruction. Keep the `output_key` values and the `{placeholder}`
names in sync — a mismatch silently yields an empty section, and the unit tests
assert the link.

This is an ADK 2.x `Workflow` graph rather than `SequentialAgent`/`ParallelAgent`,
which are deprecated in 2.6 and slated for removal.

Deterministic by construction: every run gathers all three angles. Swapping the
root for a coordinator `LlmAgent` (analysts as `sub_agents` with
`mode="single_turn"`) would buy conversational follow-ups at the cost of
predictability.
"""

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import google_search
from google.adk.workflow import START, JoinNode, RetryConfig, Workflow
from google.genai import types

from . import backends
from .tools import get_fundamentals, get_history, get_news, get_quote

# Flash for the bounded extraction the analysts do; Pro-class reasoning is not
# needed until the synthesis step. Three parallel Flash calls also mean wall
# clock is the slowest analyst, not the sum of all three.
ANALYST_MODEL = "gemini-3.6-flash"
WRITER_MODEL = "gemini-3.6-flash"

NO_GUESSING = (
    " Report only values your tools returned. If a value is missing or null, write"
    " 'n/a'. Never estimate a number or recall one from memory."
    " If a tool comes back with an `error` key, state plainly that the data is"
    " unavailable and quote the reason — do not substitute your own knowledge of"
    " the company, and do not stay silent, because the report still needs your"
    " section."
)


# Guards the JoinNode: a node that dies without emitting output leaves `gather`
# waiting forever, so the analysts retry their whole turn on failure. This is
# node-level and distinct from the per-HTTP-call retry in `_model` below.
ANALYST_RETRY = RetryConfig(max_attempts=2, initial_delay=1.0, backoff_factor=2.0)


def _model(name: str) -> Gemini:
    """Build a Gemini model with the retry policy used across this project."""
    return Gemini(model=name, retry_options=types.HttpRetryOptions(attempts=3))


fundamentals_analyst = LlmAgent(
    name="fundamentals_analyst",
    model=_model(ANALYST_MODEL),
    description="Valuation multiples, margins, growth, and balance-sheet health.",
    instruction=(
        "You are an equity fundamentals analyst. Call `get_fundamentals` for the"
        " ticker in the user's request, then summarize in short bullets:\n"
        "- Sector, industry, market cap\n"
        "- Valuation: trailing and forward P/E, price/sales, EV/EBITDA\n"
        "- Profitability: gross margin, net margin, return on equity\n"
        "- Growth: revenue and earnings growth\n"
        "- Balance sheet: debt/equity, free cash flow\n"
        "Margins and growth arrive as decimal fractions — render 0.63663 as"
        " 63.7%. Close with one line judging whether the multiple looks rich,"
        " fair, or cheap relative to the growth rate." + NO_GUESSING
    ),
    tools=[get_fundamentals],
    output_key="fundamentals",
    retry_config=ANALYST_RETRY,
)

technical_analyst = LlmAgent(
    name="technical_analyst",
    model=_model(ANALYST_MODEL),
    description="Price action, trend, and key levels.",
    instruction=(
        "You are a technical analyst. Call `get_quote`, then `get_history` with"
        " period='1y'. Report in short bullets:\n"
        "- Current price and percent day move\n"
        "- One-year return\n"
        "- Where the price sits in its 52-week range (percent of the way up)\n"
        "- Price versus the 50- and 200-day moving averages, and whether the"
        " 50-day is above or below the 200-day\n"
        "- The shape of the month-end closes: trending, ranging, or choppy\n"
        "`get_quote` returns an intraday price while `get_history` returns the"
        " last completed daily close, so the two can disagree. Lead with the"
        " intraday price, and if they differ by more than 1%, say so explicitly"
        " and give the close with its date rather than presenting both as if"
        " they agree.\n"
        "Close with one line calling the trend: uptrend, downtrend, or range-bound."
        + NO_GUESSING
    ),
    tools=[get_quote, get_history],
    output_key="technicals",
    retry_config=ANALYST_RETRY,
)

# `google_search` is a live web call, so leaving it on under the fixtures
# backend would put nondeterminism straight back into a run that exists to be
# reproducible — and it did: an unknown ticker still came back with real
# headlines. Unlike the data backend, which resolves per call, an agent's tool
# list is fixed when this module is imported.
_OFFLINE = backends.active_backend_name() == "fixtures"
_NEWS_TOOLS = [get_news] if _OFFLINE else [get_news, google_search]
_SEARCH_CLAUSE = (
    ""
    if _OFFLINE
    else (
        " Use `google_search` only to fill a genuine gap — an upcoming earnings"
        " date, guidance, or regulatory action the headlines allude to but do"
        " not explain."
    )
)

news_analyst = LlmAgent(
    name="news_analyst",
    model=_model(ANALYST_MODEL),
    description="Recent material news, catalysts, and sentiment.",
    instruction=(
        "You are a market news analyst. Call `get_news` for the ticker."
        + _SEARCH_CLAUSE
        + "\nReturn 3-6 items that could plausibly move the stock, each as:"
        " date — headline — [bullish/bearish/neutral] — one line on why it"
        " matters. Skip listicles, price-target churn, and 'best stocks to buy'"
        " content. If nothing material surfaced, say so rather than padding."
        + NO_GUESSING
    ),
    tools=_NEWS_TOOLS,
    output_key="news",
    retry_config=ANALYST_RETRY,
)

# A JoinNode only proceeds once every predecessor has emitted output — if one
# analyst dies without emitting, the graph stalls here. Hence the retry policy
# on the analysts below: all three depend on flaky network calls.
gather = JoinNode(name="gather")

report_writer = LlmAgent(
    name="report_writer",
    model=_model(WRITER_MODEL),
    description="Assembles the analysts' findings into a research memo.",
    instruction=(
        "You are the senior analyst writing the final memo. Use ONLY the three"
        " findings below — add no facts of your own.\n\n"
        "FUNDAMENTALS:\n{fundamentals}\n\n"
        "TECHNICALS:\n{technicals}\n\n"
        "NEWS:\n{news}\n\n"
        "Write these sections in order:\n"
        "**Snapshot** — two sentences: what the company is and where the stock stands.\n"
        "**Fundamentals** — valuation, profitability, growth, balance sheet.\n"
        "**Technicals** — trend, levels, momentum.\n"
        "**News & Catalysts** — what is moving or about to move the stock.\n"
        "**Risks** — three or four concrete risks drawn from the findings above,"
        " not generic market boilerplate.\n"
        "**Bottom Line** — bullish, bearish, or neutral, then one paragraph of"
        " reasoning.\n\n"
        "Where the analysts disagree — a cheap multiple against a broken trend,"
        " say — surface the tension explicitly instead of averaging it away.\n"
        "If a section's findings are empty or unavailable, say so plainly.\n"
        "End with: *Research only, not investment advice.*"
    ),
)

root_agent = Workflow(
    name="stock_research",
    description="Researches a stock across fundamentals, technicals, and news.",
    edges=[
        (START, fundamentals_analyst, gather),
        (START, technical_analyst, gather),
        (START, news_analyst, gather),
        (gather, report_writer),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
