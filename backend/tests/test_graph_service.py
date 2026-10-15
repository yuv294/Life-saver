"""Dependency graph, cascade analysis and skill clustering (pure logic, no DB)."""

from types import SimpleNamespace

from services.graph_service import (
    build_dependency_dag,
    detect_skill_clusters,
    get_cascade_severity,
    get_critical_path,
    jaccard_similarity,
)


def t(tid, hours=1.0, tags=None, deps=None):
    return SimpleNamespace(
        id=tid, title=f"task {tid}", estimated_hours=hours, skill_tags=tags or [],
        deadline=None, status="pending", depends_on=deps or [],
    )


# ── Jaccard similarity ────────────────────────────────────────────────────────

def test_jaccard_basic_cases():
    assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard_similarity({"a"}, {"b"}) == 0.0
    assert jaccard_similarity({"a", "b"}, {"b", "c"}) == 1 / 3
    assert jaccard_similarity(set(), set()) == 1.0


# ── dependency DAG / cascade ──────────────────────────────────────────────────

def test_dag_edges_follow_dependencies_and_ignore_unknown_ids():
    G = build_dependency_dag([t("a"), t("b", deps=["a"]), t("c", deps=["missing"])])
    assert set(G.edges) == {("a", "b")}
    assert set(G.nodes) == {"a", "b", "c"}


def test_cascade_severity_counts_all_downstream_tasks():
    G = build_dependency_dag([t("a"), t("b", deps=["a"]), t("c", deps=["b"]), t("d")])
    res = get_cascade_severity(G, "a")
    assert res["cascade_severity"] == 2
    assert set(res["at_risk_task_ids"]) == {"b", "c"}
    assert get_cascade_severity(G, "c")["cascade_severity"] == 0
    assert get_cascade_severity(G, "d")["cascade_severity"] == 0


def test_cascade_for_unknown_task_is_empty():
    G = build_dependency_dag([t("a")])
    assert get_cascade_severity(G, "nope") == {
        "cascade_severity": 0, "at_risk_task_ids": [], "critical_path_affected": False,
    }


# ── critical path (regression: used hop count instead of hours) ───────────────

def test_critical_path_is_longest_by_hours_not_by_number_of_tasks():
    # a(1h) -> b(1h) -> c(1h)   = 3h over 3 tasks
    # x(10h) -> y(1h)           = 11h over 2 tasks   <- critical path
    tasks = [
        t("a", 1), t("b", 1, deps=["a"]), t("c", 1, deps=["b"]),
        t("x", 10), t("y", 1, deps=["x"]),
    ]
    assert get_critical_path(build_dependency_dag(tasks)) == ["x", "y"]


def test_critical_path_of_a_chain_is_the_whole_chain():
    G = build_dependency_dag([t("a", 2), t("b", 3, deps=["a"]), t("c", 1, deps=["b"])])
    assert get_critical_path(G) == ["a", "b", "c"]


def test_critical_path_flags_cascade():
    G = build_dependency_dag([t("a", 2), t("b", 3, deps=["a"]), t("side", 1)])
    assert get_cascade_severity(G, "a")["critical_path_affected"] is True
    assert get_cascade_severity(G, "side")["critical_path_affected"] is False


def test_cycle_does_not_crash_critical_path():
    G = build_dependency_dag([t("a", deps=["b"]), t("b", deps=["a"])])
    assert get_critical_path(G) == []


def test_empty_graph_critical_path():
    assert get_critical_path(build_dependency_dag([])) == []


# ── skill clustering ──────────────────────────────────────────────────────────

def test_clusters_group_tasks_by_shared_skills():
    tasks = [
        t("1", 1, ["analytical"]), t("2", 2, ["analytical"]), t("3", 1, ["analytical"]),
        t("4", 1, ["communicative"]), t("5", 1, ["communicative"]),
    ]
    clusters = detect_skill_clusters(tasks)
    by_skill = {c["dominant_skill"]: c for c in clusters}
    assert set(by_skill) == {"analytical", "communicative"}
    assert set(by_skill["analytical"]["task_ids"]) == {"1", "2", "3"}
    assert by_skill["analytical"]["estimated_total_hours"] == 4
    assert by_skill["analytical"]["name"] == "Analytical Session"


def test_clusters_are_sorted_by_total_hours_descending():
    tasks = [t("1", 5, ["creative"]), t("2", 5, ["creative"]), t("3", 1, ["physical"]), t("4", 1, ["physical"])]
    hours = [c["estimated_total_hours"] for c in detect_skill_clusters(tasks)]
    assert hours == sorted(hours, reverse=True)


def test_single_task_and_no_tasks():
    only = detect_skill_clusters([t("1", 2, ["creative"])])
    assert len(only) == 1 and only[0]["task_ids"] == ["1"] and only[0]["dominant_skill"] == "creative"
    assert detect_skill_clusters([]) == []
