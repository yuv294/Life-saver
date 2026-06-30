"""
NetworkX-based task dependency graph, cascade analysis, skill clustering,
and Louvain community detection for cognitive session batching.
"""

import networkx as nx
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.task import Task
import logging
from itertools import combinations

logger = logging.getLogger(__name__)

SKILL_TAGS = ["analytical", "creative", "communicative", "administrative", "relational", "physical"]


def jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def build_dependency_dag(tasks: List[Task]) -> nx.DiGraph:
    G = nx.DiGraph()
    task_map = {str(t.id): t for t in tasks}
    for task in tasks:
        G.add_node(
            str(task.id),
            title=task.title,
            estimated_hours=task.estimated_hours or 1.0,
            skill_tags=task.skill_tags or [],
            deadline=str(task.deadline) if task.deadline else None,
            status=task.status,
        )
    for task in tasks:
        for dep_id in (task.depends_on or []):
            if dep_id in task_map:
                G.add_edge(dep_id, str(task.id))
    return G


def get_critical_path(G: nx.DiGraph) -> List[str]:
    if not G.nodes:
        return []
    try:
        return nx.dag_longest_path(G, weight="estimated_hours")
    except nx.NetworkXUnfeasible:
        logger.warning("Cycle detected in dependency graph — critical path unavailable")
        return []


def get_cascade_severity(G: nx.DiGraph, task_id: str) -> Dict[str, Any]:
    if task_id not in G:
        return {"cascade_severity": 0, "at_risk_task_ids": [], "critical_path_affected": False}
    descendants = nx.descendants(G, task_id)
    critical = get_critical_path(G)
    return {
        "cascade_severity": len(descendants),
        "at_risk_task_ids": list(descendants),
        "critical_path_affected": task_id in critical,
        "at_risk_titles": [G.nodes[d].get("title", "") for d in descendants],
    }


def build_skill_similarity_graph(tasks: List[Task]) -> nx.Graph:
    """Nodes = tasks, edges = Jaccard similarity of skill_tags > 0.3."""
    G = nx.Graph()
    for task in tasks:
        G.add_node(str(task.id), title=task.title, skill_tags=task.skill_tags or [])
    for t1, t2 in combinations(tasks, 2):
        sim = jaccard_similarity(set(t1.skill_tags or []), set(t2.skill_tags or []))
        if sim >= 0.3:
            G.add_edge(str(t1.id), str(t2.id), weight=sim)
    return G


def detect_skill_clusters(tasks: List[Task]) -> List[Dict[str, Any]]:
    """
    Louvain community detection on the skill-similarity graph.
    Falls back to manual grouping by primary skill if networkx_louvain is unavailable.
    """
    if len(tasks) < 2:
        if tasks:
            t = tasks[0]
            return [{
                "task_ids": [str(t.id)],
                "dominant_skill": (t.skill_tags or ["administrative"])[0],
                "skill_tags": list(set(t.skill_tags or [])),
                "estimated_total_hours": t.estimated_hours or 1.0,
                "name": f"{(t.skill_tags or ['work'])[0].capitalize()} Session",
            }]
        return []

    G = build_skill_similarity_graph(tasks)

    # Try Louvain; fall back to greedy modularity
    try:
        from networkx.algorithms.community import louvain_communities
        communities = louvain_communities(G, seed=42)
    except Exception:
        try:
            from networkx.algorithms.community import greedy_modularity_communities
            communities = list(greedy_modularity_communities(G))
        except Exception:
            # Final fallback: group by primary skill tag
            communities = _group_by_primary_skill(tasks)

    task_map = {str(t.id): t for t in tasks}
    clusters = []
    for community in communities:
        node_ids = list(community)
        cluster_tasks = [task_map[nid] for nid in node_ids if nid in task_map]
        all_tags = [tag for t in cluster_tasks for tag in (t.skill_tags or [])]
        dominant = max(set(all_tags), key=all_tags.count) if all_tags else "administrative"
        total_hours = sum(t.estimated_hours or 1.0 for t in cluster_tasks)
        clusters.append({
            "task_ids": node_ids,
            "dominant_skill": dominant,
            "skill_tags": list(set(all_tags)),
            "estimated_total_hours": total_hours,
            "name": f"{dominant.capitalize()} Session",
        })

    return sorted(clusters, key=lambda c: c["estimated_total_hours"], reverse=True)


def _group_by_primary_skill(tasks: List[Task]) -> List[set]:
    groups: Dict[str, set] = {}
    for task in tasks:
        key = (task.skill_tags or ["administrative"])[0]
        groups.setdefault(key, set()).add(str(task.id))
    return list(groups.values())


class GraphService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _load_tasks(self, user_id: str) -> List[Task]:
        result = await self.db.execute(
            select(Task).where(
                Task.user_id == user_id,
                Task.status.in_(["pending", "in_progress"]),
            )
        )
        return list(result.scalars().all())

    async def cascade_analysis(self, task_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        tasks = await self._load_tasks(user_id) if user_id else []
        if not tasks:
            result = await self.db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                tasks = await self._load_tasks(str(task.user_id))

        G = build_dependency_dag(tasks)
        return get_cascade_severity(G, task_id)

    async def get_clusters(self, user_id: str) -> List[Dict[str, Any]]:
        tasks = await self._load_tasks(user_id)
        return detect_skill_clusters(tasks)

    async def get_critical_path(self, user_id: str) -> List[str]:
        tasks = await self._load_tasks(user_id)
        G = build_dependency_dag(tasks)
        return get_critical_path(G)
