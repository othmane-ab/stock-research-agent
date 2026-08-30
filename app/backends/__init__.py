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

"""Selects where market data comes from.

    MARKET_DATA_BACKEND=fixtures   # default: canned snapshot, no network
    MARKET_DATA_BACKEND=live       # yfinance

Both modules expose the same four callables, so `app.tools` does not care
which one is active. Resolved per call rather than cached at import, so tests
can flip the env var with monkeypatch.
"""

import os
from types import ModuleType

from . import fixtures, live

_BACKENDS: dict[str, ModuleType] = {"fixtures": fixtures, "live": live}

DEFAULT_BACKEND = "fixtures"


def active_backend_name() -> str:
    """Return the configured backend name, normalized."""
    return os.environ.get("MARKET_DATA_BACKEND", DEFAULT_BACKEND).strip().lower()


def active_backend() -> ModuleType:
    """Return the backend module named by MARKET_DATA_BACKEND."""
    name = active_backend_name()
    try:
        return _BACKENDS[name]
    except KeyError:
        raise ValueError(
            f"Unknown MARKET_DATA_BACKEND {name!r}. "
            f"Expected one of: {', '.join(sorted(_BACKENDS))}."
        ) from None
