# services/metrics.py — 진행률/평균점수/최근활동 (개선판)
from __future__ import annotations
from typing import Tuple, Optional, List
from sqlalchemy import func
from extensions import db
from models import Enrollment, Assignment, Submission, Message

def assignment_progress_for_user(uid: int) -> Tuple[int, int, int]:
    """
    진행률(%) / 제출완료 과제수 / 전체 과제수
    - 전체 과제수: 내가 수강 중인 강좌의 Assignment 개수 (distinct)
    - 제출완료 과제수: 내가 제출한(Submitted_at not null) Submission의 assignment_id distinct 개수
      (재제출/여러 번 제출해도 1건으로 계산)
    """
    # 전체 과제 수 (내 수강 강좌 범위)
    total = db.session.scalar(
        db.select(func.count(func.distinct(Assignment.id)))
        .join(Enrollment, Enrollment.course_id == Assignment.course_id)
        .where(Enrollment.user_id == uid)
    ) or 0

    # 제출 완료 과제 수 (내 수강 강좌 범위로 제한)
    submitted = db.session.scalar(
        db.select(func.count(func.distinct(Submission.assignment_id)))
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .join(Enrollment, Enrollment.course_id == Assignment.course_id)
        .where(
            Enrollment.user_id == uid,
            Submission.user_id == uid,
            Submission.submitted_at.isnot(None),
        )
    ) or 0

    pct = int(round(100 * submitted / total)) if total else 0
    return pct, int(submitted), int(total)


def average_score_for_user(uid: int) -> Optional[float]:
    """
    과제별 점수를 만점 대비 %로 환산한 뒤 평균.
    - total_score가 NULL이면 100으로 간주
    - 제출에 점수가 있는 경우만 포함
    반환: 소수 1자리까지 반올림한 float (예: 87.3) 또는 None
    """
    avg_pct = db.session.scalar(
        db.select(
            func.avg(
                100.0 * Submission.score / func.nullif(func.coalesce(Assignment.total_score, 100), 0)
            )
        )
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .where(
            Submission.user_id == uid,
            Submission.score.isnot(None),
        )
    )
    return round(float(avg_pct), 1) if avg_pct is not None else None


def recent_activities_for_user(uid: int, limit: int = 5) -> List[Message]:
    """
    간단 대체: 최근 메시지 기준 활동.
    필요 시 ActivityLog 등으로 교체 가능.
    """
    rows = (
        db.session.query(Message)
        .filter((Message.receiver_id == uid) | (Message.sender_id == uid))
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    return rows