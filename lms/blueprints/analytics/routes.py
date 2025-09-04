from datetime import datetime, timedelta
from flask import Blueprint, render_template
from sqlalchemy import func, extract
from helpers.auth import roles_required
from models import db, User, Course, Enrollment, Assignment, Submission
# 관리자/교수 전용 페이지

bp = Blueprint("analytics", __name__, url_prefix="/analytics")

@bp.get("/", endpoint="home")
@roles_required("admin", "instructor")
def page():
    student_count = db.session.scalar(db.select(func.count(User.id))) or 0
    active_courses = db.session.scalar(db.select(func.count(func.distinct(Enrollment.course_id)))) or 0

    course_assign_cnt = {
        cid: cnt
        for cid, cnt in db.session.execute(
            db.select(Assignment.course_id, func.count(Assignment.id)).group_by(Assignment.course_id)
        ).all()
    }
    enrolled_by_course = {
        cid: cnt
        for cid, cnt in db.session.execute(
            db.select(Enrollment.course_id, func.count(Enrollment.user_id)).group_by(Enrollment.course_id)
        ).all()
    }

    expected_submissions = sum(
        (course_assign_cnt.get(cid, 0) * enrolled_by_course.get(cid, 0))
        for cid in set([*course_assign_cnt.keys(), *enrolled_by_course.keys()])
    )
    submitted_total = db.session.scalar(
        db.select(func.count(Submission.id)).where(Submission.submitted_at.isnot(None))
    ) or 0
    avg_progress_global = int(round(100 * submitted_total / expected_submissions)) if expected_submissions else 0

    # 강좌별 완료율
    courses_with_hw = [cid for cid, n in course_assign_cnt.items() if n > 0]
    finished_pairs, total_pairs = 0, 0
    if courses_with_hw:
        rows = db.session.execute(
            db.select(Submission.user_id, Assignment.course_id, func.count(Submission.id))
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .where(Submission.submitted_at.isnot(None), Assignment.course_id.in_(courses_with_hw))
            .group_by(Submission.user_id, Assignment.course_id)
        ).all()
        submap = {(u, c): n for (u, c, n) in rows}
        enrolls = db.session.execute(
            db.select(Enrollment.user_id, Enrollment.course_id).where(Enrollment.course_id.in_(courses_with_hw))
        ).all()
        total_pairs = len(enrolls)
        for u, c in enrolls:
            need = course_assign_cnt.get(c, 0)
            if need and submap.get((u, c), 0) >= need:
                finished_pairs += 1
    completion_rate = int(round(100 * finished_pairs / total_pairs)) if total_pairs else 0

    # 코스 성과 카드
    course_perf = []
    course_rows = db.session.execute(db.select(Course.id, Course.title)).all()

    subrows = db.session.execute(
        db.select(Submission.user_id, Assignment.course_id, func.count(Submission.id))
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .where(Submission.submitted_at.isnot(None))
        .group_by(Submission.user_id, Assignment.course_id)
    ).all()
    submap_all = {}
    for u, c, n in subrows:
        submap_all.setdefault(c, {})[u] = n

    for cid, title in course_rows:
        enrolled_cnt = enrolled_by_course.get(cid, 0)
        need = course_assign_cnt.get(cid, 0)
        completed_cnt = 0
        if need and enrolled_cnt:
            user_ids = [u for (u,) in db.session.execute(
                db.select(Enrollment.user_id).where(Enrollment.course_id == cid)
            ).all()]
            for u in user_ids:
                if submap_all.get(cid, {}).get(u, 0) >= need:
                    completed_cnt += 1
        course_perf.append({"title": title, "enrolled": enrolled_cnt, "completed": completed_cnt})

    # 월간 트렌드(최근 5개월)
    end = datetime.utcnow().replace(day=1)
    start = (end - timedelta(days=31 * 4)).replace(day=1)
    monthly = {
        (int(y), int(m)): cnt
        for (y, m, cnt) in db.session.execute(
            db.select(
                extract("year", Submission.submitted_at),
                extract("month", Submission.submitted_at),
                func.count(Submission.id),
            )
            .where(
                Submission.submitted_at.isnot(None),
                Submission.submitted_at >= start,
                Submission.submitted_at < end + timedelta(days=40),
            )
            .group_by(extract("year", Submission.submitted_at), extract("month", Submission.submitted_at))
        ).all()
    }
    trend, cur = [], start
    for _ in range(5):
        key = (cur.year, cur.month)
        sub_cnt = int(monthly.get(key, 0))
        month_label = f"{cur.month}월"
        avg_pct = int(round(100 * sub_cnt / expected_submissions)) if expected_submissions else 0
        trend.append({"month": month_label, "avg_progress": avg_pct, "submissions": sub_cnt})
        cur = cur.replace(year=cur.year + 1, month=1) if cur.month == 12 else cur.replace(month=cur.month + 1)

    metrics = {
        "student_count": student_count,
        "student_growth": "+0%",
        "active_courses": active_courses,
        "new_courses": "+0%",
        "avg_progress": trend[-1]["avg_progress"] if trend else avg_progress_global,
        "progress_growth": "+0%",
        "completion_rate": completion_rate,
        "completion_growth": "+0%",
    }

    # 상세/위험군
    avg_score_by_course = {
        cid: (float(avg) if avg is not None else None)
        for cid, avg in db.session.execute(
            db.select(Assignment.course_id, func.avg(Submission.score))
            .join(Submission, Submission.assignment_id == Assignment.id)
            .where(Submission.score.isnot(None))
            .group_by(Assignment.course_id)
        ).all()
    }

    enrolled_by_course = {
        cid: cnt
        for cid, cnt in db.session.execute(
            db.select(Enrollment.course_id, func.count(Enrollment.user_id)).group_by(Enrollment.course_id)
        ).all()
    }

    course_details = []
    for cid, title in course_rows:
        students = enrolled_by_course.get(cid, 0)
        avg_sc = avg_score_by_course.get(cid, None)
        need = course_assign_cnt.get(cid, 0)
        completed_cnt = 0
        if need and students:
            user_ids = [u for (u,) in db.session.execute(
                db.select(Enrollment.user_id).where(Enrollment.course_id == cid)
            ).all()]
            for u in user_ids:
                if submap_all.get(cid, {}).get(u, 0) >= need:
                    completed_cnt += 1
        completion = int(round(100 * completed_cnt / students)) if students else 0
        course_details.append(
            {"title": title, "students": students, "avg_score": (round(avg_sc, 0) if avg_sc is not None else None), "completion": completion}
        )

    # 간단 위험군 (상위 3명)
    expected_by_user = {
        uid: cnt
        for uid, cnt in db.session.execute(
            db.select(Enrollment.user_id, func.count(Assignment.id))
            .join(Assignment, Assignment.course_id == Enrollment.course_id)
            .group_by(Enrollment.user_id)
        ).all()
    }
    submitted_by_user = {
        uid: cnt
        for uid, cnt in db.session.execute(
            db.select(Submission.user_id, func.count(Submission.id))
            .where(Submission.submitted_at.isnot(None))
            .group_by(Submission.user_id)
        ).all()
    }
    avg_by_user = {
        uid: float(avg)
        for uid, avg in db.session.execute(
            db.select(Submission.user_id, func.avg(Submission.score))
            .where(Submission.score.isnot(None))
            .group_by(Submission.user_id)
        ).all()
    }

    try:
        student_rows = db.session.execute(
            db.select(User.id, User.name, User.email).where(User.role == "student")
        ).all()
    except Exception:
        student_rows = db.session.execute(
            db.select(User.id, User.name, User.email)
            .join(Enrollment, Enrollment.user_id == User.id)
            .group_by(User.id, User.name, User.email)
        ).all()

    risk_students = []
    for uid, name, email in student_rows:
        expected = expected_by_user.get(uid, 0)
        submitted = submitted_by_user.get(uid, 0)
        progress = int(round(100 * submitted / expected)) if expected else 0
        avg_sc = avg_by_user.get(uid, None)
        badges = []
        if progress < 40:
            badges.append("낮은 진도율")
        if expected and (submitted / expected) < 0.5:
            badges.append("낮은 과제 제출률")
        if avg_sc is not None and avg_sc < 60:
            badges.append("낮은 평균 점수")
        if badges:
            risk_students.append(
                {"name": name, "email": email, "progress": progress, "submission_rate": progress,
                 "avg_score": int(round(avg_sc)) if avg_sc is not None else None, "badges": badges}
            )
    def _risk_key(s): return (s["progress"], s["avg_score"] if s["avg_score"] is not None else 999)
    risk_students.sort(key=_risk_key)
    risk_students = risk_students[:3]

    return render_template(
        "analytics.html",
        metrics=metrics,
        course_perf=course_perf,
        trend=trend,
        course_details=course_details,
        risk_students=risk_students,
    )