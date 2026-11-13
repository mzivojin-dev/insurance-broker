from types import SimpleNamespace as NS

from agent_core import Agent
from agent_core.tools import tool


@tool
def add(a: int, b: int) -> int:
    """Adds two integers together."""
    return a + b


class FakeClient:
    def __init__(self, responses):
        self.calls = []

        def create(**kwargs):
            self.calls.append(kwargs)
            return responses.pop(0)

        self.messages = NS(create=create)


def resp(content, stop, tokens=10):
    usage = NS(input_tokens=tokens, output_tokens=tokens)
    return NS(content=content, stop_reason=stop, usage=usage)


def text(t):
    return NS(type="text", text=t)


def use(i, a, b):
    return NS(type="tool_use", id=f"t{i}", name="add", input={"a": a, "b": b})


def test_runs_tool_then_keeps_final_answer_and_counts_all_tokens():
    client = FakeClient([
        resp([text("Let me add. "), use(1, 2, 2)], "tool_use"),
        resp([text("The answer is 4.")], "end_turn"),
    ])
    t = Agent(system_prompt="math", client=client, tools=[add]).run("What is 2 + 2?")

    assert t.output_text == "Let me add. The answer is 4."
    assert [(c.name, c.args, c.result) for c in t.tool_calls] == [("add", {"a": 2, "b": 2}, 4)]
    assert (t.input_tokens, t.output_tokens) == (20, 20)
    assert t.error is None
    # the tool result went back to the model on the second call
    assert client.calls[1]["messages"][-1]["content"][0]["content"] == "4"


def test_stops_at_max_turns():
    loop = [resp([use(i, 1, 1)], "tool_use") for i in range(10)]
    t = Agent(system_prompt="", tools=[add], client=FakeClient(loop), max_turns=3).run("go")
    assert t.error == "max_turns" and len(t.tool_calls) == 3


def test_stops_when_token_budget_exceeded():
    loop = [resp([use(i, 1, 1)], "tool_use", tokens=30) for i in range(10)]
    t = Agent(system_prompt="", tools=[add], client=FakeClient(loop), token_budget=100).run("go")
    assert t.error == "token_budget"
    assert t.input_tokens + t.output_tokens == 120  # stopped on the 2nd response, which crossed 100


def test_tool_errors_are_returned_to_the_model():
    client = FakeClient([
        resp([NS(type="tool_use", id="t1", name="add", input={"a": "x", "b": 1})], "tool_use"),
        resp([text("Sorry.")], "end_turn"),
    ])
    t = Agent(system_prompt="", tools=[add], client=client).run("go")
    assert str(t.tool_calls[0].result).startswith("error:")
    assert t.output_text == "Sorry."
