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

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent


def test_agent_researches_a_ticker_end_to_end() -> None:
    """Run the full graph on one ticker and assert every stage contributed.

    Runs on the fixtures backend (the default), so the market data is fixed and
    only the model varies. Still hits Vertex, so it is slow and needs credentials.
    """

    session_service = InMemorySessionService()

    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Research NVDA")]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )
    assert len(events) > 0, "Expected at least one message"

    # Every analyst must have run its tools; the memo is only as good as these.
    called = {
        part.function_call.name
        for event in events
        if event.content and event.content.parts
        for part in event.content.parts
        if part.function_call
    }
    assert {"get_fundamentals", "get_quote", "get_history", "get_news"} <= called, (
        f"Expected all four market data tools to be called, got {called}"
    )

    # The join must have fired and each analyst must have written its state key.
    final = session_service.get_session_sync(
        app_name="test", user_id="test_user", session_id=session.id
    )
    for key in ("fundamentals", "technicals", "news"):
        assert final.state.get(key), f"Analyst never wrote state[{key!r}]"

    memo = "\n".join(
        part.text
        for event in events
        if event.author == "report_writer" and event.content and event.content.parts
        for part in event.content.parts
        if part.text
    )
    assert memo.strip(), "report_writer produced no memo"
    for heading in ("Fundamentals", "Technicals", "Risks", "Bottom Line"):
        assert heading in memo, f"Memo is missing the {heading} section"
