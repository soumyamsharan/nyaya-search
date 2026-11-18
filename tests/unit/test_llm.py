import json
import threading
import time

import httpx
import pytest

from nyaya.errors import LlmBusyError, LlmUnavailableError
from nyaya.llm import GuardedLlm, LlmResult, OpenAICompatibleClient
from tests.fakes import FakeCallLog, FakeChatClient


def client(*responses: httpx.Response) -> tuple[OpenAICompatibleClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return queue.pop(0)

    return OpenAICompatibleClient("http://llm.test/v1", "m", "secret", transport=httpx.MockTransport(handler)), seen


def ok(content: dict) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}}],
                                     "usage": {"prompt_tokens": 5, "completion_tokens": 2}})


def test_json_completion_and_auth_header():
    c, seen = client(ok({"a": 1}))
    result = c.complete_json("sys", "user")
    assert result.content == {"a": 1} and result.tokens_in == 5
    assert seen[0].headers["Authorization"] == "Bearer secret"
    assert json.loads(seen[0].content)["response_format"] == {"type": "json_object"}


def test_rate_limit_is_waited_out_then_succeeds():
    waits: list[float] = []
    seen: list[httpx.Request] = []
    queue = [httpx.Response(429, headers={"retry-after": "1"}), ok({"c": 3})]

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return queue.pop(0)

    c = OpenAICompatibleClient("http://llm.test/v1", "m", transport=httpx.MockTransport(handler), sleep=waits.append)
    assert c.complete_json("s", "u").content == {"c": 3}
    assert waits == [1.0] and len(seen) == 2


def test_rate_limit_gives_up_when_the_wait_budget_is_spent():
    waits: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "1"})

    c = OpenAICompatibleClient("http://llm.test/v1", "m", transport=httpx.MockTransport(handler),
                               rate_limit_wait=3, sleep=waits.append)
    with pytest.raises(LlmBusyError):
        c.complete_json("s", "u")
    assert sum(waits) <= 3


class SlowChat:
    model = "m"

    def __init__(self) -> None:
        self.running = 0
        self.most_at_once = 0
        self._lock = threading.Lock()

    def complete_json(self, system: str, user: str):
        with self._lock:
            self.running += 1
            self.most_at_once = max(self.most_at_once, self.running)
        time.sleep(0.05)
        with self._lock:
            self.running -= 1
        return LlmResult({"ok": True}, 1, 1)


def test_model_calls_run_one_at_a_time():
    chat = SlowChat()
    guard = GuardedLlm(chat, FakeCallLog(), 100)
    threads = [threading.Thread(target=guard.run, args=("q", "v1", "s", "u", lambda c: (c, 0))) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert chat.most_at_once == 1


def test_queued_request_gives_up_when_its_turn_does_not_come():
    chat = SlowChat()
    guard = GuardedLlm(chat, FakeCallLog(), 100, queue_wait=0.01)
    first = threading.Thread(target=guard.run, args=("q", "v1", "s", "u", lambda c: (c, 0)))
    first.start()
    time.sleep(0.01)
    with pytest.raises(LlmBusyError):
        guard.run("q", "v1", "s", "u", lambda c: (c, 0))
    first.join()


def test_server_error_is_retried_once():
    c, seen = client(httpx.Response(500), ok({"b": 2}))
    assert c.complete_json("s", "u").content == {"b": 2}
    assert len(seen) == 2


def test_malformed_output_is_unavailable():
    c, _ = client(httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]}))
    with pytest.raises(LlmUnavailableError):
        c.complete_json("s", "u")


def test_daily_cap_blocks_the_call_and_records_it():
    calls = FakeCallLog(today=10)
    chat = FakeChatClient({"x": 1})
    with pytest.raises(LlmBusyError):
        GuardedLlm(chat, calls, daily_cap=10).run("question", "v1", "s", "u", lambda c: (c, 0))
    assert chat.calls == []
    assert calls.rows[0]["outcome"] == "capped"


def test_successful_call_logs_metadata_only():
    calls = FakeCallLog()
    question = "my client's confidential facts"
    value = GuardedLlm(FakeChatClient({"x": 1}), calls, daily_cap=10).run(
        "question", "v1", "system", question, lambda c: (c["x"], 3))
    assert value == 1
    row = calls.rows[0]
    assert row["outcome"] == "ok" and row["sentences_dropped"] == 3
    assert question not in json.dumps(row)


def test_provider_failure_is_logged_and_raised():
    calls = FakeCallLog()
    with pytest.raises(LlmUnavailableError):
        GuardedLlm(FakeChatClient(error=LlmUnavailableError("down")), calls, 10).run("q", "v1", "s", "u",
                                                                                   lambda c: (c, 0))
    assert calls.rows[0]["outcome"] == "llm_unavailable"
