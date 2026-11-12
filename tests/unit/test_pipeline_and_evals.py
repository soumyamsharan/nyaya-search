from nyaya.domain import SearchMode
from nyaya.text import normalize_citation as n
from nyaya_evals.runner import ModeResult, gate_failure, percentile, score
from nyaya_pipeline.report import RunReport
from nyaya_pipeline.stages import build_aliases


def test_parallel_citation_resolves_through_case_law_cited():
    own = {n("[2007] 3 SCR 507"): "B"}
    aliases = build_aliases(own, ["State of Goa v. Sanjay Thakran [2007] 3 SCR 507 : (2007) 3 SCC 755"])
    assert aliases[n("(2007) 3 SCC 755")] == "B"


def test_ambiguous_alias_group_is_not_guessed():
    own = {n("[2007] 3 SCR 507"): "B", n("[2008] 1 SCR 1"): "C"}
    aliases = build_aliases(own, ["X [2007] 3 SCR 507 : (2007) 3 SCC 755 : [2008] 1 SCR 1"])
    assert n("(2007) 3 SCC 755") not in aliases
    assert aliases[n("[2007] 3 SCR 507")] == "B"


def test_unknown_citation_stays_unresolved():
    assert n("(1999) 1 SCC 1") not in build_aliases({}, ["Y (1999) 1 SCC 1"])


def test_run_report_fails_above_threshold():
    report = RunReport("extract")
    report.counts["processed"] = 10
    for i in range(2):
        report.fail(f"j{i}", "boom")
    assert report.outcome(max_failure_share=0.1) == "failed"
    assert report.outcome(max_failure_share=0.5) == "ok"


def test_eval_scores():
    assert score(["A", "B", "C"], ["B"]) == (1.0, 0.5)
    assert score(["A"], ["B", "C"]) == (0.0, 0.0)
    assert percentile([10, 20, 30, 40], 95) == 40


def test_eval_gate():
    bm25 = ModeResult(SearchMode.BM25.value, 0.6, 0.5, 10, 20)
    worse = ModeResult(SearchMode.HYBRID_RERANK.value, 0.5, 0.5, 10, 20)
    better = ModeResult(SearchMode.HYBRID_RERANK.value, 0.7, 0.6, 10, 20)
    assert gate_failure({"bm25": bm25, "hybrid_rerank": worse})
    assert gate_failure({"bm25": bm25, "hybrid_rerank": better}) is None
