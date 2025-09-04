# services/metrics.py — 진행률/평균점수/최근활동
from __future__ import annotations
from typing import Tuple, Optional
from sqlalchemy import func
from extensions import db
from models import Enrollment, Assignment, Submission, Message

def assignment_progress_for_user(uid: int) -> Tuple[int, int, int]:
    total = db.session.query(Assignment)\
        .join(Enrollment, Enrollment.course_id == Assignment.course_id)\
        .filter(Enrollment.user_id == uid).count()
    submitted = db.session.query(Submission)\
        .filter(Submission.user_id == uid, Submission.submitted_at.isnot(None)).count()
    pct = int(round(100 * submitted / total)) if total else 0
    return pct, submitted, total

def average_score_for_user(uid: int) -> Optional[float]:
    avg = db.session.scalar(
        db.select(func.avg(Submission.score))
        .where(Submission.user_id == uid, Submission.score.isnot(None))
    )
    return float(avg) if avg is not None else None

def recent_activities_for_user(uid: int, limit: int = 5):
    # 간단히 메시지 최신 순으로 대체(활동 로그 없을 때)
    rows = (db.session.query(Message)
            .filter((Message.receiver_id == uid) | (Message.sender_id == uid))
            .order_by(Message.created_at.desc()).limit(limit).all())
    return rows