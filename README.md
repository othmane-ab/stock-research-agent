# stock-research-agent

Collaborative equity research agent. Three specialist analysts fan out over a
ticker concurrently, then a writer synthesizes their findings into one memo.

```
START ->  fundamentals_analyst  -> state["fundamentals"]  -.
START ->  technical_analyst     -> state["technicals"]     :-> gather -> report_writer
START ->  news_analyst          -> state["news"]          -'
```

Built as an ADK 2.x `Workflow` graph. The analysts run in parallel off `START`
and re-join at a `JoinNode`, so wall-clock time is the slowest analyst rather
than the sum of all three. They never see each other's work — they communicate
only by writing to distinct session-state keys via `output_key`, which
`report_writer` reads back by name in its instruction.

`SequentialAgent`/`ParallelAgent` would express the same shape but are
deprecated in ADK 2.6 and slated for removal.

Ask it `Research NVDA` and it returns a memo with Snapshot, Fundamentals,
Technicals, News & Catalysts, Risks, and a Bottom Line call.

## Project Structure

```
stock-research-agent/
├── app/         # Core agent code
│   ├── agent.py               # The Workflow graph: 3 analysts + writer
│   ├── tools.py               # Tool schema layer, dispatches to a backend
│   ├── backends/
│   │   ├── fixtures.py        # Canned snapshot (default) — no network
│   │   └── live.py            # yfinance
│   ├── fast_api_app.py        # FastAPI Backend server
│   └── app_utils/             # App utilities and helpers
├── scripts/refresh_fixtures.py  # Re-snapshot live data into fixtures
├── tests/                     # Unit (offline), integration (live), load
├── AGENTS.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

## Market data backends

```bash
MARKET_DATA_BACKEND=fixtures   # default: canned snapshot, no network
MARKET_DATA_BACKEND=live       # yfinance
```

`app/tools.py` is a thin schema layer — its docstrings and type hints are what
the model sees — and dispatches to whichever backend is selected. The two
modules expose the same four callables, so nothing above them changes.

**Fixtures are the default** so runs are reproducible: the same numbers every
time, no network, no rate limits, and eval scores that stay comparable across
days. The data is a real yfinance snapshot (2026-08-30) rather than invented
figures, so its shapes and edge cases match what `live` actually returns.
Refresh it with `uv run python scripts/refresh_fixtures.py [TICKER ...]`, and
expect eval scores to shift afterwards — the agent's inputs changed.

Under `fixtures`, `news_analyst` also **loses its `google_search` tool**.
That tool is a live web call, so leaving it on would put nondeterminism right
back into a run that exists to be reproducible.

| Tool | Returns |
|---|---|
| `get_quote` | Intraday price, day move, 52-week range, market cap |
| `get_history` | Dated first/last closes, 1y return, 50/200-day MAs, month-end closes |
| `get_fundamentals` | Sector, valuation multiples, margins, growth, leverage |
| `get_news` | Recent headlines with publisher, date, summary |

## Failure handling

Every tool returns a dict with an `error` key rather than raising when a ticker
is unknown. That is load-bearing, not politeness: an analyst node that raises
dies without emitting output, and the `JoinNode` would then wait for it
forever. The analysts are instructed to report the gap, so an unresearchable
ticker still yields a memo saying so instead of hanging or inventing numbers.
The analysts also carry a `RetryConfig` for the same reason.

Three real quirks the backends normalize, each with a test:

- yfinance emits a **`NaN` close** for the in-progress session. Dropped in
  `_closes` — otherwise last close, return, and both moving averages silently
  go null.
- `get_quote` is an **intraday** quote while `get_history` ends at the last
  **completed** session, so they legitimately disagree. Both carry as-of dates
  and `technical_analyst` is told to reconcile them rather than report both as
  if they agree.
- Yahoo signals an unknown symbol **two different ways**: `None` prices for a
  delisted-but-known symbol, a raised `KeyError` for one it has never heard of.

> 💡 **Tip:** Use [Antigravity CLI](https://antigravity.google/) for AI-assisted development - project context is pre-configured in `AGENTS.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start

Install `agents-cli` and its skills if not already installed:

```bash
uvx google-agents-cli setup
```

Install required packages:

```bash
agents-cli install
```

Test the agent with a local web server:

```bash
agents-cli playground
```

You can also use features from the [ADK](https://adk.dev/) CLI with `uv run adk`.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `agents-cli eval`    | Evaluate agent behavior (generate, grade, analyze, and more — see `agents-cli eval --help`) |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        |
| `agents-cli deploy`  | Deploy agent to Agent Runtime                                                                |
| `agents-cli publish gemini-enterprise` | Register deployed agent to Gemini Enterprise                    || [A2A Inspector](https://github.com/a2aproject/a2a-inspector) | Launch A2A Protocol Inspector                                                        |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

To add CI/CD and Terraform, run `agents-cli scaffold enhance`.
To set up your production infrastructure, run `agents-cli infra cicd`.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.

## A2A Inspector

This agent supports the [A2A Protocol](https://a2a-protocol.org/). Use the [A2A Inspector](https://github.com/a2aproject/a2a-inspector) to test interoperability.
See the [A2A Inspector docs](https://github.com/a2aproject/a2a-inspector) for details.
