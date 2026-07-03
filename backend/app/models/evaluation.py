import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Evaluation(Base):
    """SQLAlchemy model for AI response evaluations."""

    __tablename__ = "ai_response_evaluations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id: Mapped[str] = mapped_column(String(100), nullable=True)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_context: Mapped[str] = mapped_column(Text, nullable=False)
    ai_response: Mapped[str] = mapped_column(Text, nullable=False)
    faithfulness_score: Mapped[float] = mapped_column(Float, nullable=False)
    answer_relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    context_precision_score: Mapped[float] = mapped_column(Float, nullable=False)
    context_recall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    evaluation_framework: Mapped[str] = mapped_column(String(20), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Evaluation id={self.id} framework={self.evaluation_framework} overall_score={self.overall_score}>"
