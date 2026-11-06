"""Each eval case is one pytest test. A case passes when its worst run meets its threshold."""

from evals.harness.runner import run_case


def test_case(case, request):
    runs = [run_case(case) for _ in range(request.config.getoption("runs"))]
    worst = min(runs, key=lambda r: r.score)
    assert worst.score >= case.threshold, worst.error or worst.explain()
