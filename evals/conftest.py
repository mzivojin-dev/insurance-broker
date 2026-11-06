"""Lets you run evals as pytest for the red/green loop on one feature:

    uv run pytest evals --agent client_service --tag escalation -v
"""


def pytest_addoption(parser):
    parser.addoption("--agent", default=None, help="only this agent's cases")
    parser.addoption("--tag", default="smoke", help="smoke | full | regression | all | any tag")
    parser.addoption("--runs", type=int, default=1, help="runs per case; passes on the worst run")


def pytest_generate_tests(metafunc):
    if "case" in metafunc.fixturenames:
        from evals.harness.case import load_cases

        cases = load_cases(agent=metafunc.config.getoption("agent"),
                           tag=metafunc.config.getoption("tag"))
        metafunc.parametrize("case", cases, ids=[c.id for c in cases])


def pytest_configure(config):
    config.addinivalue_line("markers", "eval: calls a model; not run by plain `pytest`")
