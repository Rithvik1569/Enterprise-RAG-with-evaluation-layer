from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List

from app.core.dependencies import require_admin
from app.database import get_db
from app.models.user import User
from app.models.evaluation import Evaluation
from app.schemas.auth import UserOut

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[UserOut]:
    """Return all registered users. Admin role required."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [UserOut.model_validate(u) for u in users]


@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Dict[str, Any]:
    """Computes RAG SaaS evaluations analytics: faithfulness, latency, hallucination rates over time.

    Admin role required.
    """
    # 1. Fetch all evaluations sorted by date
    result = await db.execute(select(Evaluation).order_by(Evaluation.created_at.asc()))
    evaluations = result.scalars().all()

    total_requests = len(evaluations)
    if total_requests == 0:
        return {
            "summary": {
                "total_requests": 0,
                "avg_faithfulness": 0.0,
                "avg_relevance": 0.0,
                "avg_precision": 0.0,
                "avg_recall": 0.0,
                "avg_latency_ms": 0.0,
                "hallucination_rate": 0.0,
            },
            "daily_stats": [],
            "recent_evaluations": [],
        }

    # 2. Compute Summary Metrics
    sum_faithfulness = 0.0
    sum_relevance = 0.0
    sum_precision = 0.0
    sum_recall = 0.0
    sum_latency = 0.0
    hallucination_count = 0

    for ev in evaluations:
        sum_faithfulness += ev.faithfulness_score
        sum_relevance += ev.answer_relevance_score
        sum_precision += ev.context_precision_score
        sum_recall += ev.context_recall_score
        sum_latency += ev.latency_ms if ev.latency_ms is not None else 0.0
        
        # Consider it a hallucination if faithfulness score is below 80% (0.8)
        if ev.faithfulness_score < 0.8:
            hallucination_count += 1

    summary = {
        "total_requests": total_requests,
        "avg_faithfulness": round(sum_faithfulness / total_requests, 4),
        "avg_relevance": round(sum_relevance / total_requests, 4),
        "avg_precision": round(sum_precision / total_requests, 4),
        "avg_recall": round(sum_recall / total_requests, 4),
        "avg_latency_ms": round(sum_latency / total_requests, 2),
        "hallucination_rate": round(hallucination_count / total_requests, 4),
    }

    # 3. Compute Daily Aggregations (safe on both SQLite/PostgreSQL by parsing string in Python)
    daily_groups = defaultdict(list)
    for ev in evaluations:
        # Format date as YYYY-MM-DD
        date_str = ev.created_at.strftime("%Y-%m-%d")
        daily_groups[date_str].append(ev)

    daily_stats = []
    for date_str, ev_list in sorted(daily_groups.items()):
        daily_total = len(ev_list)
        d_sum_faithfulness = sum(e.faithfulness_score for e in ev_list)
        d_sum_latency = sum((e.latency_ms if e.latency_ms is not None else 0.0) for e in ev_list)
        d_hallucinations = sum(1 for e in ev_list if e.faithfulness_score < 0.8)

        daily_stats.append({
            "date": date_str,
            "count": daily_total,
            "avg_faithfulness": round(d_sum_faithfulness / daily_total, 4),
            "avg_latency_ms": round(d_sum_latency / daily_total, 2),
            "hallucination_rate": round(d_hallucinations / daily_total, 4),
        })

    # 4. Grab Recent 20 Evaluations
    recent_evals = []
    # Reverse order for recents (newest first)
    for ev in reversed(evaluations[-20:]):
        recent_evals.append({
            "id": ev.id,
            "user_query": ev.user_query[:60] + "..." if len(ev.user_query) > 60 else ev.user_query,
            "overall_score": ev.overall_score,
            "faithfulness_score": ev.faithfulness_score,
            "answer_relevance_score": ev.answer_relevance_score,
            "context_precision_score": ev.context_precision_score,
            "context_recall_score": ev.context_recall_score,
            "latency_ms": ev.latency_ms,
            "created_at": ev.created_at.isoformat(),
        })

    return {
        "summary": summary,
        "daily_stats": daily_stats,
        "recent_evaluations": recent_evals,
    }
