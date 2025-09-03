# app.py
from flask import Flask, render_template, request, abort, url_for, flash, redirect
from sqlalchemy import func, or_, extract
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os

# ===== Models =====
from models import (
    db, User, Course, Enrollment, Assignment, Submission,
    assignment_progress_for_user, average_score_for_user,
    recent_activities_for_user, upcoming_items_for_user,
    MentoringTeam, MentoringTeamMember, MentoringReport,
    Project, ProjectTask, Competition, CompetitionEntry,
    Message, CalendarEvent,
    UserSetting,          # ← 추가
)

# ------------------------------------------------------------------------------
# App Config
# ------------------------------------------------------------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://wsuser:wsuser!@127.0.0.1:3306/lms_db?charset=utf8mb4"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")  # flash 등 세션용
db.init_app(app)

DEMO_USER_ID = 1

# 업로드 디렉터리 & 허용 확장자
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTS = {
    'pdf','zip','doc','docx','ppt','pptx','xlsx','csv','ipynb','py','txt','md','rar'
}
def _allowed(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTS

# ------------------------------------------------------------------------------
# Jinja Filters & Helpers
# ------------------------------------------------------------------------------
@app.template_filter('ymd_kr')
def ymd_kr(dt):
    if not dt: return ''
    return f"{dt.year}. {dt.month}. {dt.day}."

@app.template_filter('dt_kr')
def dt_kr(dt):
    if not dt: return ''
    return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d} {dt.hour:02d}:{dt.minute:02d}"

@app.context_processor
def inject_helpers():
    def active_exact(endpoint_or_path='/'):
        p = request.path
        if endpoint_or_path.startswith('/'):
            return p == endpoint_or_path
        try:
            return p == url_for(endpoint_or_path)
        except Exception:
            return False
    def active_prefix(path_prefix):
        return request.path.startswith(path_prefix)
    return dict(active_exact=active_exact, active_prefix=active_prefix)

# ------------------------------------------------------------------------------
# 1) Dashboard
# ------------------------------------------------------------------------------
@app.route('/')
def dashboard():
    user = db.session.get(User, DEMO_USER_ID)
    if not user:
        return "초기 데이터가 없습니다. MariaDB에서 init_db.sql을 먼저 실행하세요.", 500

    course_count = db.session.query(Enrollment).filter_by(user_id=DEMO_USER_ID).count()
    progress_pct, submitted_cnt, total_cnt = assignment_progress_for_user(DEMO_USER_ID)
    avg_score = average_score_for_user(DEMO_USER_ID)

    bars = []
    courses = (db.session.query(Course)
               .join(Enrollment, Enrollment.course_id == Course.id)
               .filter(Enrollment.user_id == DEMO_USER_ID)
               .all())
    for c in courses:
        total_c = db.session.query(Assignment).filter_by(course_id=c.id).count()
        submitted_c = (db.session.query(Submission)
                       .join(Assignment, Assignment.id == Submission.assignment_id)
                       .filter(Submission.user_id == DEMO_USER_ID,
                               Assignment.course_id == c.id,
                               Submission.submitted_at.isnot(None))
                       .count())
        pct = int((submitted_c / total_c) * 100) if total_c else 0
        bars.append({'course': c, 'pct': pct})

    upcoming = upcoming_items_for_user(DEMO_USER_ID, within_days=21)
    recent = recent_activities_for_user(DEMO_USER_ID, limit=5)

    return render_template('dashboard.html',
                           user=user,
                           course_count=course_count,
                           progress_pct=progress_pct,
                           submitted_cnt=submitted_cnt,
                           total_cnt=total_cnt,
                           avg_score=avg_score,
                           bars=bars,
                           upcoming=upcoming,
                           recent=recent)

# ------------------------------------------------------------------------------
# 2) Courses
# ------------------------------------------------------------------------------
@app.route('/courses')
def courses():
    rows = (db.session.query(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == DEMO_USER_ID)
            .all())
    cards = []
    for c in rows:
        total = db.session.query(Assignment).filter_by(course_id=c.id).count()
        submitted = (db.session.query(Submission)
                     .join(Assignment, Assignment.id == Submission.assignment_id)
                     .filter(Submission.user_id == DEMO_USER_ID,
                             Assignment.course_id == c.id,
                             Submission.submitted_at.isnot(None))
                     .count())
        pct = int((submitted / total) * 100) if total else 0
        cards.append({'course': c, 'total': total, 'submitted': submitted, 'progress': pct})
    return render_template('courses.html', courses=cards)

# ------------------------------------------------------------------------------
# 3) Course Detail
# ------------------------------------------------------------------------------
@app.route('/course/<int:course_id>')
def course_detail(course_id):
    tab = request.args.get('tab', 'materials')
    course = db.session.get(Course, course_id)
    if not course:
        abort(404, description="강좌를 찾을 수 없습니다.")

    total = db.session.query(Assignment).filter_by(course_id=course.id).count()
    submitted = (db.session.query(Submission)
                 .join(Assignment, Assignment.id == Submission.assignment_id)
                 .filter(Submission.user_id == DEMO_USER_ID,
                         Assignment.course_id == course.id,
                         Submission.submitted_at.isnot(None))
                 .count())
    progress_pct = int((submitted / total) * 100) if total else 0

    assignments = (db.session.query(Assignment)
                   .filter_by(course_id=course.id)
                   .order_by(func.isnull(Assignment.due_at), Assignment.due_at.asc())
                   .all())

    sub_map = {
        s.assignment_id: s
        for s in (db.session.query(Submission)
                  .join(Assignment, Assignment.id == Submission.assignment_id)
                  .filter(Submission.user_id == DEMO_USER_ID, Assignment.course_id == course.id)
                  .all())
    }

    materials = [
        {"week": 1, "title": "1주차: HTML 기초", "duration": "45분", "status": "완료"},
        {"week": 2, "title": "2주차: CSS 스타일링", "duration": "50분", "status": "완료"},
        {"week": 3, "title": "3주차: JavaScript 기초", "duration": "60분", "status": "진행중"},
        {"week": None, "title": "실습 자료 - HTML 템플릿", "size": "2.5MB", "download": True},
    ]
    notices = [
        {"title": "중간고사 안내", "date": "2025-03-05", "pin": True},
        {"title": "실습 자료 업데이트", "date": "2025-02-28", "pin": False},
    ]
    discussion = [
        {"title": "1주차 과제 질문 스레드", "comments": 12, "updated": "2시간 전"},
        {"title": "프로젝트 팀 편성", "comments": 8, "updated": "1일 전"},
    ]

    return render_template('course_detail.html',
                           course=course, tab=tab,
                           progress_pct=progress_pct,
                           assignments=assignments, sub_map=sub_map,
                           materials=materials, notices=notices, discussion=discussion)

# ------------------------------------------------------------------------------
# 4) Messages
# ------------------------------------------------------------------------------
@app.route('/messages')
def messages_page():
    tab = request.args.get('tab', 'inbox')  # inbox | sent | compose
    q = (request.args.get('q') or '').strip()

    base_inbox = db.session.query(Message).filter(Message.receiver_id == DEMO_USER_ID)
    base_sent = db.session.query(Message).filter(Message.sender_id == DEMO_USER_ID)

    if q:
        like = f"%{q}%"
        base_inbox = base_inbox.join(User, Message.sender_id == User.id).filter(
            or_(Message.title.like(like), Message.body.like(like), User.name.like(like))
        )
        base_sent = base_sent.join(User, Message.receiver_id == User.id).filter(
            or_(Message.title.like(like), Message.body.like(like), User.name.like(like))
        )

    inbox = base_inbox.order_by(Message.read_at.is_(None).desc(),
                                Message.created_at.desc()).all()
    sent = base_sent.order_by(Message.created_at.desc()).all()
    users = db.session.query(User).filter(User.id != DEMO_USER_ID).order_by(User.name.asc()).all()

    unread_cnt = db.session.scalar(
        db.select(func.count(Message.id)).where(
            Message.receiver_id == DEMO_USER_ID, Message.read_at.is_(None)
        )
    ) or 0

    return render_template('messages.html',
                           tab=tab, q=q,
                           inbox=inbox, sent=sent, users=users, unread_cnt=unread_cnt)

@app.route('/messages/<int:msg_id>')
def message_detail(msg_id):
    m = db.session.get(Message, msg_id)
    if not m or (m.sender_id != DEMO_USER_ID and m.receiver_id != DEMO_USER_ID):
        abort(404)
    if m.receiver_id == DEMO_USER_ID and m.read_at is None:
        m.read_at = datetime.utcnow()
        db.session.commit()
    return render_template('message_detail.html', m=m)

@app.route('/messages/send', methods=['POST'])
def messages_send():
    to_id = request.form.get('to_id')
    title = (request.form.get('title') or '').strip()
    body = (request.form.get('body') or '').strip()
    if not to_id or not to_id.isdigit() or not title:
        flash('받는 사람과 제목은 필수입니다.', 'error')
        return redirect(url_for('messages_page', tab='compose'))

    msg = Message(sender_id=DEMO_USER_ID, receiver_id=int(to_id), title=title, body=body)
    db.session.add(msg); db.session.commit()
    flash('메시지를 보냈습니다.', 'success')
    return redirect(url_for('messages_page', tab='sent'))

@app.route('/messages/reply/<int:msg_id>', methods=['POST'])
def messages_reply(msg_id):
    src = db.session.get(Message, msg_id)
    if not src or (src.sender_id != DEMO_USER_ID and src.receiver_id != DEMO_USER_ID):
        abort(404)
    to_id = src.sender_id if src.receiver_id == DEMO_USER_ID else src.receiver_id
    title = (request.form.get('title') or f"Re: {src.title}").strip()
    body = (request.form.get('body') or '').strip()
    if not title:
        flash('제목은 필수입니다.', 'error')
        return redirect(url_for('message_detail', msg_id=msg_id))
    msg = Message(sender_id=DEMO_USER_ID, receiver_id=to_id, title=title, body=body)
    db.session.add(msg); db.session.commit()
    flash('답장을 보냈습니다.', 'success')
    return redirect(url_for('messages_page', tab='sent'))

# ------------------------------------------------------------------------------
# 5) Schedule (Calendar + Assignment deadlines)
# ------------------------------------------------------------------------------
@app.route('/schedule')
def schedule_page():
    days = int(request.args.get('days', 30))
    start_param = request.args.get('start')  # YYYY-MM-DD
    end_param = request.args.get('end')
    q = (request.args.get('q') or '').strip()
    include_assign = (request.args.get('assign', '1') == '1')

    now = datetime.utcnow()
    start = now
    end = now + timedelta(days=days)
    try:
        if start_param: start = datetime.strptime(start_param, "%Y-%m-%d")
        if end_param:   end = datetime.strptime(end_param, "%Y-%m-%d")
    except Exception:
        pass

    ev_q = (db.session.query(CalendarEvent)
            .filter(CalendarEvent.start_at >= start,
                    CalendarEvent.start_at <= end,
                    or_(CalendarEvent.user_id == None, CalendarEvent.user_id == DEMO_USER_ID)))
    if q:
        like = f"%{q}%"
        ev_q = ev_q.filter(or_(CalendarEvent.title.like(like),
                               CalendarEvent.location.like(like),
                               CalendarEvent.description.like(like)))
    events = ev_q.order_by(CalendarEvent.start_at.asc()).all()

    items = []
    for e in events:
        items.append({
            "id": e.id, "kind": e.kind or "event",
            "title": e.title, "course": e.course.title if e.course else None,
            "start": e.start_at, "end": e.end_at, "location": e.location,
            "is_event": True
        })

    if include_assign:
        arows = (db.session.query(Assignment, Course)
                 .join(Course, Course.id == Assignment.course_id)
                 .join(Enrollment, Enrollment.course_id == Course.id)
                 .filter(Enrollment.user_id == DEMO_USER_ID,
                         Assignment.due_at.isnot(None),
                         Assignment.due_at >= start,
                         Assignment.due_at <= end)
                 .all())
        for a, c in arows:
            items.append({
                "id": None, "kind": "assignment",
                "title": a.title, "course": c.title,
                "start": a.due_at, "end": None, "location": None,
                "is_event": False
            })

    items.sort(key=lambda x: (x["start"] or datetime.max))

    my_courses = (db.session.query(Course)
                  .join(Enrollment, Enrollment.course_id == Course.id)
                  .filter(Enrollment.user_id == DEMO_USER_ID)
                  .order_by(Course.title.asc()).all())

    return render_template("schedule.html",
                           items=items, start=start, end=end, q=q,
                           include_assign=include_assign, courses=my_courses)

@app.route('/schedule/new', methods=['POST'])
def schedule_new():
    title = (request.form.get('title') or '').strip()
    start_at = request.form.get('start_at')  # 'YYYY-MM-DDTHH:MM'
    end_at = request.form.get('end_at')
    location = (request.form.get('location') or '').strip()
    kind = (request.form.get('kind') or 'event').strip()
    course_id = request.form.get('course_id')
    description = (request.form.get('description') or '').strip()

    if not title or not start_at:
        flash("제목과 시작 일시는 필수입니다.", "error")
        return redirect(url_for('schedule_page'))

    def parse_dt(s):
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
            try: return datetime.strptime(s, fmt)
            except Exception: pass
        return None

    sdt = parse_dt(start_at)
    edt = parse_dt(end_at) if end_at else None
    if not sdt:
        flash("시작 일시 형식이 올바르지 않습니다.", "error")
        return redirect(url_for('schedule_page'))
    if end_at and not edt:
        flash("종료 일시 형식이 올바르지 않습니다.", "error")
        return redirect(url_for('schedule_page'))

    cid = int(course_id) if course_id and course_id.isdigit() else None

    ev = CalendarEvent(
        user_id=DEMO_USER_ID, course_id=cid, title=title,
        start_at=sdt, end_at=edt, location=location or None,
        kind=kind or 'event', description=description or None, source='manual'
    )
    db.session.add(ev); db.session.commit()
    flash("일정이 추가되었습니다.", "success")
    return redirect(url_for('schedule_page'))

@app.route('/schedule/delete/<int:event_id>', methods=['POST'])
def schedule_delete(event_id):
    ev = db.session.get(CalendarEvent, event_id)
    if not ev or not (ev.user_id is None or ev.user_id == DEMO_USER_ID):
        abort(404)
    db.session.delete(ev); db.session.commit()
    flash("일정이 삭제되었습니다.", "success")
    return redirect(url_for('schedule_page'))

# ------------------------------------------------------------------------------
# 6) Assignments (업로드/재제출/지각 표시)
# ------------------------------------------------------------------------------
@app.route('/assignments')
def assignments_page():
    rows = (db.session.query(Assignment, Course)
            .join(Course, Course.id == Assignment.course_id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == DEMO_USER_ID)
            .order_by(Assignment.due_at.is_(None), Assignment.due_at.asc())
            .all())
    subs = (db.session.query(Submission)
            .filter(Submission.user_id == DEMO_USER_ID)
            .all())
    sub_map = {s.assignment_id: s for s in subs}
    return render_template('assignments.html', rows=rows, sub_map=sub_map)

@app.route('/assignments/submit/<int:aid>', methods=['POST'])
def assignment_submit(aid):
    # 내 과제 여부 확인
    enrolled = (db.session.query(Assignment.id, Assignment.due_at)
                .join(Course, Assignment.course_id == Course.id)
                .join(Enrollment, Enrollment.course_id == Course.id)
                .filter(Enrollment.user_id == DEMO_USER_ID, Assignment.id == aid)
                .first())
    if not enrolled:
        abort(403)

    file = request.files.get('file')
    comment = (request.form.get('comment') or '').strip()

    file_url = None
    if file and file.filename:
        if not _allowed(file.filename):
            flash("허용되지 않은 파일 형식입니다.", "error")
            return redirect(url_for('assignments_page'))
        fname = secure_filename(file.filename)
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        uniq = f"u{DEMO_USER_ID}_a{aid}_{ts}_{fname}"
        save_path = os.path.join(UPLOAD_DIR, uniq)
        file.save(save_path)
        file_url = f"/static/uploads/{uniq}"

    # upsert
    sub = (db.session.query(Submission)
           .filter_by(assignment_id=aid, user_id=DEMO_USER_ID)
           .first())
    now = datetime.utcnow()
    if not sub:
        sub = Submission(assignment_id=aid, user_id=DEMO_USER_ID)
        db.session.add(sub)
    if file_url:
        sub.file_url = file_url
    if comment:
        sub.comment = comment
    sub.submitted_at = now
    sub.updated_at = now
    db.session.commit()

    due_at = enrolled.due_at
    if due_at and now > due_at:
        flash("제출되었습니다. (지각 제출)", "success")
    else:
        flash("제출되었습니다.", "success")
    return redirect(url_for('assignments_page'))

# ------------------------------------------------------------------------------
# 7) Mentoring Hub
# ------------------------------------------------------------------------------
@app.route('/mentoring')
def mentoring_home():
    tab = request.args.get('tab', 'reports')  # reports|teams|projects|competitions|github

    my_teams = (db.session.query(MentoringTeam)
                .join(MentoringTeamMember)
                .filter(MentoringTeamMember.user_id == DEMO_USER_ID)
                .all())

    my_reports = (db.session.query(MentoringReport)
                  .filter_by(author_user_id=DEMO_USER_ID)
                  .order_by(MentoringReport.created_at.desc()).all())

    teams_owned = db.session.query(MentoringTeam).filter_by(owner_user_id=DEMO_USER_ID).all()

    # 프로젝트: (내가 owner) OR (내 팀에 속한 프로젝트)
    conds = [Project.owner_user_id == DEMO_USER_ID]
    team_ids = [t.id for t in my_teams]
    if team_ids:
        conds.append(Project.team_id.in_(team_ids))
    my_projects = (db.session.query(Project)
                   .filter(or_(*conds))
                   .order_by(Project.created_at.desc())
                   .all())

    comps = (db.session.query(Competition)
             .order_by(func.isnull(Competition.apply_deadline),  # NULL LAST 효과
                       Competition.apply_deadline.asc())
             .all())

    entry_conds = [CompetitionEntry.applicant_user_id == DEMO_USER_ID]
    if team_ids:
        entry_conds.append(CompetitionEntry.team_id.in_(team_ids))
    my_entries = (db.session.query(CompetitionEntry)
                  .filter(or_(*entry_conds))
                  .order_by(CompetitionEntry.created_at.desc())
                  .all())

    return render_template("mentoring.html",
                           tab=tab,
                           my_reports=my_reports, my_teams=my_teams, teams_owned=teams_owned,
                           my_projects=my_projects, comps=comps, my_entries=my_entries)

# 보고서 생성
@app.route('/mentoring/reports/new', methods=['POST'])
def mentoring_report_new():
    title = (request.form.get('title') or '').strip()
    content = (request.form.get('content') or '').strip()
    team_id = request.form.get('team_id')
    team_id = int(team_id) if team_id and team_id.isdigit() else None

    file = request.files.get('file')
    file_url = None
    if file and file.filename:
        fname = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_DIR, fname)
        file.save(save_path)
        file_url = f"/static/uploads/{fname}"

    if not title:
        flash("제목은 필수입니다.", "error")
    else:
        r = MentoringReport(author_user_id=DEMO_USER_ID, team_id=team_id,
                            title=title, content=content, file_url=file_url)
        db.session.add(r); db.session.commit()
        flash("보고서가 등록되었습니다.", "success")
    return redirect(url_for('mentoring_home', tab='reports'))

# 팀 생성
@app.route('/mentoring/teams/new', methods=['POST'])
def mentoring_team_new():
    name = (request.form.get('name') or '').strip()
    is_solo = bool(request.form.get('is_solo'))
    if not name:
        flash("팀 이름은 필수입니다.", "error")
        return redirect(url_for('mentoring_home', tab='teams'))
    team = MentoringTeam(name=name, owner_user_id=DEMO_USER_ID, is_solo=is_solo)
    db.session.add(team); db.session.flush()
    db.session.add(MentoringTeamMember(team_id=team.id, user_id=DEMO_USER_ID, role='leader'))
    db.session.commit()
    flash("팀이 생성되었습니다.", "success")
    return redirect(url_for('mentoring_home', tab='teams'))

# 팀 참여
@app.route('/mentoring/teams/join', methods=['POST'])
def mentoring_team_join():
    team_id = request.form.get('team_id')
    if not team_id or not team_id.isdigit():
        flash("팀 ID가 올바르지 않습니다.", "error")
        return redirect(url_for('mentoring_home', tab='teams'))
    team_id = int(team_id)
    exists = db.session.query(MentoringTeamMember).filter_by(team_id=team_id, user_id=DEMO_USER_ID).first()
    if exists:
        flash("이미 해당 팀에 속해 있습니다.", "error")
    else:
        db.session.add(MentoringTeamMember(team_id=team_id, user_id=DEMO_USER_ID, role='member'))
        db.session.commit()
        flash("팀에 참여했습니다.", "success")
    return redirect(url_for('mentoring_home', tab='teams'))

# 프로젝트 생성
@app.route('/mentoring/projects/new', methods=['POST'])
def mentoring_project_new():
    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip()
    team_id = request.form.get('team_id')
    team_id = int(team_id) if team_id and team_id.isdigit() else None
    github = (request.form.get('github') or '').strip()

    if not title:
        flash("프로젝트 제목은 필수입니다.", "error")
    else:
        p = Project(title=title, description=description, team_id=team_id,
                    owner_user_id=DEMO_USER_ID if not team_id else None,
                    github_repo_url=github or None)
        db.session.add(p); db.session.commit()
        flash("프로젝트가 생성되었습니다.", "success")
    return redirect(url_for('mentoring_home', tab='projects'))

# 작업 추가
@app.route('/mentoring/tasks/new', methods=['POST'])
def mentoring_task_new():
    project_id = request.form.get('project_id')
    title = (request.form.get('title') or '').strip()
    due_at = request.form.get('due_at')  # 'YYYY-MM-DD HH:MM'
    assignee_id = request.form.get('assignee_id')

    if not project_id or not project_id.isdigit() or not title:
        flash("프로젝트와 제목은 필수입니다.", "error")
        return redirect(url_for('mentoring_home', tab='projects'))

    dt = None
    if due_at:
        try:
            dt = datetime.strptime(due_at, "%Y-%m-%d %H:%M")
        except Exception:
            flash("마감 형식은 YYYY-MM-DD HH:MM 입니다.", "error")

    assignee_id = int(assignee_id) if assignee_id and assignee_id.isdigit() else None

    t = ProjectTask(project_id=int(project_id), title=title, due_at=dt, assignee_user_id=assignee_id)
    db.session.add(t); db.session.commit()
    flash("작업이 추가되었습니다.", "success")
    return redirect(url_for('mentoring_home', tab='projects'))

# 공모전 등록
@app.route('/mentoring/competitions/new', methods=['POST'])
def mentoring_comp_new():
    title = (request.form.get('title') or '').strip()
    host = (request.form.get('host') or '').strip()
    url_ = (request.form.get('url') or '').strip()
    deadline = request.form.get('apply_deadline')
    dt = None
    if deadline:
        try:
            dt = datetime.strptime(deadline, "%Y-%m-%d %H:%MM")
        except Exception:
            try:
                dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
            except Exception:
                flash("마감 형식은 YYYY-MM-DD HH:MM 입니다.", "error")
    if not title:
        flash("공모전 제목은 필수입니다.", "error")
    else:
        c = Competition(title=title, host=host or None, url=url_ or None, apply_deadline=dt)
        db.session.add(c); db.session.commit()
        flash("공모전이 등록되었습니다.", "success")
    return redirect(url_for('mentoring_home', tab='competitions'))

# 공모전 신청
@app.route('/mentoring/competitions/apply', methods=['POST'])
def mentoring_comp_apply():
    competition_id = request.form.get('competition_id')
    team_id = request.form.get('team_id')
    project_id = request.form.get('project_id')
    if not competition_id or not competition_id.isdigit():
        flash("공모전 ID가 올바르지 않습니다.", "error")
        return redirect(url_for('mentoring_home', tab='competitions'))

    entry = CompetitionEntry(
        competition_id=int(competition_id),
        team_id=int(team_id) if team_id and team_id.isdigit() else None,
        applicant_user_id=DEMO_USER_ID,
        project_id=int(project_id) if project_id and project_id.isdigit() else None,
        status='submitted'
    )
    db.session.add(entry); db.session.commit()
    flash("공모전에 신청했습니다.", "success")
    return redirect(url_for('mentoring_home', tab='competitions'))

# ------------------------------------------------------------------------------
# 8) Analytics
# ------------------------------------------------------------------------------
@app.route('/analytics')
def analytics_page():
    student_count = db.session.scalar(db.select(func.count(User.id))) or 0
    active_courses = db.session.scalar(
        db.select(func.count(func.distinct(Enrollment.course_id)))
    ) or 0

    course_assign_cnt = {
        cid: cnt for cid, cnt in db.session.execute(
            db.select(Assignment.course_id, func.count(Assignment.id))
            .group_by(Assignment.course_id)
        ).all()
    }
    enrolled_by_course = {
        cid: cnt for cid, cnt in db.session.execute(
            db.select(Enrollment.course_id, func.count(Enrollment.user_id))
            .group_by(Enrollment.course_id)
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
            db.select(Enrollment.user_id, Enrollment.course_id)
            .where(Enrollment.course_id.in_(courses_with_hw))
        ).all()
        total_pairs = len(enrolls)
        for u, c in enrolls:
            need = course_assign_cnt.get(c, 0)
            if need and submap.get((u, c), 0) >= need:
                finished_pairs += 1
    completion_rate = int(round(100 * finished_pairs / total_pairs)) if total_pairs else 0

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

    end = datetime.utcnow().replace(day=1)
    start = (end - timedelta(days=31*4)).replace(day=1)
    monthly = {
        (int(y), int(m)): cnt
        for (y, m, cnt) in db.session.execute(
            db.select(extract('year', Submission.submitted_at),
                      extract('month', Submission.submitted_at),
                      func.count(Submission.id))
            .where(Submission.submitted_at.isnot(None),
                   Submission.submitted_at >= start,
                   Submission.submitted_at < end + timedelta(days=40))
            .group_by(extract('year', Submission.submitted_at),
                      extract('month', Submission.submitted_at))
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

    # 상세/위험군 (동일 로직)
    avg_score_by_course = {
        cid: (float(avg) if avg is not None else None)
        for cid, avg in db.session.execute(
            db.select(Assignment.course_id, func.avg(Submission.score))
            .join(Submission, Submission.assignment_id == Assignment.id)
            .where(Submission.score.isnot(None))
            .group_by(Assignment.course_id)
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
        course_details.append({
            "title": title,
            "students": students,
            "avg_score": (round(avg_sc, 0) if avg_sc is not None else None),
            "completion": completion,
        })

    expected_by_user = {
        uid: cnt for uid, cnt in db.session.execute(
            db.select(Enrollment.user_id, func.count(Assignment.id))
            .join(Assignment, Assignment.course_id == Enrollment.course_id)
            .group_by(Enrollment.user_id)
        ).all()
    }
    submitted_by_user = {
        uid: cnt for uid, cnt in db.session.execute(
            db.select(Submission.user_id, func.count(Submission.id))
            .where(Submission.submitted_at.isnot(None))
            .group_by(Submission.user_id)
        ).all()
    }
    avg_by_user = {
        uid: float(avg) for uid, avg in db.session.execute(
            db.select(Submission.user_id, func.avg(Submission.score))
            .where(Submission.score.isnot(None))
            .group_by(Submission.user_id)
        ).all()
    }

    try:
        student_rows = db.session.execute(
            db.select(User.id, User.name, User.email).where(User.role == 'student')
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
        sub_rate = progress
        avg_sc = avg_by_user.get(uid, None)

        badges = []
        if progress < 40: badges.append("낮은 진도율")
        if expected and (submitted / expected) < 0.5: badges.append("낮은 과제 제출률")
        if avg_sc is not None and avg_sc < 60: badges.append("낮은 평균 점수")

        if badges:
            risk_students.append({
                "name": name, "email": email,
                "progress": progress, "submission_rate": sub_rate,
                "avg_score": int(round(avg_sc)) if avg_sc is not None else None,
                "badges": badges
            })
    def _risk_key(s):
        avg = s["avg_score"] if s["avg_score"] is not None else 999
        return (s["progress"], avg)
    risk_students.sort(key=_risk_key)
    risk_students = risk_students[:3]

    return render_template("analytics.html",
                           metrics=metrics,
                           course_perf=course_perf,
                           trend=trend,
                           course_details=course_details,
                           risk_students=risk_students)

# ------------------------------------------------------------------------------
# 9) Users
# ------------------------------------------------------------------------------
@app.route('/users')
def users_page():
    q = (request.args.get('q') or '').strip()
    role = request.args.get('role', 'all')  # all | student | instructor | admin
    query = db.session.query(User)
    if role in ('student', 'instructor', 'admin'):
        query = query.filter(User.role == role)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.name.like(like),
                                 User.username.like(like),
                                 User.email.like(like),
                                 User.phone.like(like)))
    users = query.order_by(User.created_at.desc()).all()
    total_cnt = db.session.scalar(db.select(func.count(User.id))) or 0
    student_cnt = db.session.scalar(db.select(func.count(User.id)).where(User.role == 'student')) or 0
    instructor_cnt = db.session.scalar(db.select(func.count(User.id)).where(User.role == 'instructor')) or 0
    admin_cnt = db.session.scalar(db.select(func.count(User.id)).where(User.role == 'admin')) or 0
    return render_template('users.html',
                           users=users,
                           total_cnt=total_cnt, student_cnt=student_cnt,
                           instructor_cnt=instructor_cnt, admin_cnt=admin_cnt,
                           q=q, role=role)

# ------------------------------------------------------------------------------
# 10) Profile & Settings
# ------------------------------------------------------------------------------
@app.route('/profile')
def profile_page():
    user = db.session.get(User, DEMO_USER_ID)
    if not user:
        return "초기 데이터가 없습니다. MariaDB에서 init_db.sql을 먼저 실행하세요.", 500
    enrolled_cnt = db.session.query(Enrollment).filter_by(user_id=DEMO_USER_ID).count()
    submitted_cnt = (db.session.query(Submission)
                     .filter(Submission.user_id == DEMO_USER_ID,
                             Submission.submitted_at.isnot(None)).count())
    avg_score = db.session.scalar(
        db.select(func.avg(Submission.score))
        .where(Submission.user_id == DEMO_USER_ID, Submission.score.isnot(None))
    )
    avg_score = round(float(avg_score), 1) if avg_score is not None else None
    return render_template("profile.html",
                           user=user,
                           enrolled_cnt=enrolled_cnt,
                           submitted_cnt=submitted_cnt,
                           avg_score=avg_score)

@app.route('/profile/update', methods=['POST'])
def profile_update():
    user = db.session.get(User, DEMO_USER_ID)
    if not user:
        return "초기 데이터가 없습니다. MariaDB에서 init_db.sql을 먼저 실행하세요.", 500

    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip()
    phone = (request.form.get('phone') or '').strip()
    username = (request.form.get('username') or '').strip()

    errors = []
    if not name: errors.append("이름은 필수입니다.")
    if not email: errors.append("이메일은 필수입니다.")
    if email:
        exists = (db.session.query(User)
                  .filter(User.email == email, User.id != user.id)
                  .first())
        if exists: errors.append("이미 사용 중인 이메일입니다.")

    if errors:
        flash(" / ".join(errors), "error")
        return redirect(url_for('profile_page'))

    user.name = name
    user.email = email
    user.phone = phone or None
    user.username = username or None
    db.session.commit()
    flash("프로필이 저장되었습니다.", "success")
    return redirect(url_for('profile_page'))

# ------------------------------------------------------------------------------
# Settings (환경설정)
# ------------------------------------------------------------------------------
@app.route('/settings')
def settings_page():
    # 설정 레코드가 없으면 기본 생성
    s = db.session.query(UserSetting).filter_by(user_id=DEMO_USER_ID).first()
    if not s:
        s = UserSetting(user_id=DEMO_USER_ID)
        db.session.add(s); db.session.commit()
    return render_template('settings.html', s=s)

@app.route('/settings/update', methods=['POST'])
def settings_update():
    s = db.session.query(UserSetting).filter_by(user_id=DEMO_USER_ID).first()
    if not s:
        s = UserSetting(user_id=DEMO_USER_ID)
        db.session.add(s)

    s.language = (request.form.get('language') or 'ko').strip()
    s.theme = (request.form.get('theme') or 'light').strip()
    s.timezone = (request.form.get('timezone') or 'Asia/Seoul').strip()
    s.email_notifications = True if request.form.get('email_notifications') else False
    s.push_notifications  = True if request.form.get('push_notifications') else False
    s.updated_at = datetime.utcnow()

    db.session.commit()
    flash("설정이 저장되었습니다.", "success")
    return redirect(url_for('settings_page'))

# ------------------------------------------------------------------------------
# Grades (성적)
# ------------------------------------------------------------------------------
@app.route('/grades')
def grades_page():
    # 내가 듣는 강좌
    courses = (db.session.query(Course)
               .join(Enrollment, Enrollment.course_id == Course.id)
               .filter(Enrollment.user_id == DEMO_USER_ID)
               .order_by(Course.title.asc())
               .all())

    course_cards = []   # 상단 표(강좌별 요약)
    details = {}        # 강좌별 과제 상세 (템플릿에서 펼쳐 보여줌)

    overall_avgs = []   # 전체 평균 계산용

    for c in courses:
        # 해당 강좌 과제 / 제출
        assigns = (db.session.query(Assignment)
                   .filter(Assignment.course_id == c.id)
                   .order_by(func.isnull(Assignment.due_at), Assignment.due_at.asc())
                   .all())

        subs = (db.session.query(Submission)
                .join(Assignment, Assignment.id == Submission.assignment_id)
                .filter(Submission.user_id == DEMO_USER_ID,
                        Assignment.course_id == c.id)
                .all())
        sub_map = {s.assignment_id: s for s in subs}

        total = len(assigns)
        submitted = len([s for s in subs if s.submitted_at is not None])
        graded = [s for s in subs if s.score is not None]
        graded_cnt = len(graded)

        ontime = 0
        late = 0
        for s in graded:
            if s.assignment and s.assignment.due_at and s.submitted_at:
                if s.submitted_at > s.assignment.due_at:
                    late += 1
                else:
                    ontime += 1

        # 평균: 각 채점된 과제의 백분율 평균
        avg_pct = None
        if graded_cnt:
            acc = 0.0
            for s in graded:
                total_score = s.assignment.total_score or 100
                acc += (float(s.score) / float(total_score)) * 100.0
            avg_pct = round(acc / graded_cnt, 1)
            overall_avgs.append(avg_pct)

        completion = int(round(100 * submitted / total)) if total else 0

        # 레터 그레이드
        def letter(p):
            if p is None: return '-'
            return 'A' if p >= 90 else 'B' if p >= 80 else 'C' if p >= 70 else 'D' if p >= 60 else 'F'

        course_cards.append({
            "course": c,
            "total": total,
            "submitted": submitted,
            "graded": graded_cnt,
            "ontime": ontime,
            "late": late,
            "missing": max(total - submitted, 0),
            "avg_pct": avg_pct,
            "letter": letter(avg_pct),
            "completion": completion,
        })

        # 상세 테이블 데이터 (과제별)
        rows = []
        for a in assigns:
            s = sub_map.get(a.id)
            status = '미제출'
            pct = None
            late_badge = None
            if s and s.submitted_at:
                status = '제출'
                if a.due_at and s.submitted_at > a.due_at:
                    late_badge = '지각'
            if s and s.score is not None:
                pct = round((s.score / float(a.total_score or 100)) * 100.0, 1)
            rows.append({
                "a": a,
                "s": s,
                "status": status,
                "pct": pct,
                "late_badge": late_badge
            })
        details[c.id] = rows

    overall_avg = round(sum(overall_avgs)/len(overall_avgs), 1) if overall_avgs else None

    return render_template("grades.html",
                           cards=course_cards,
                           details=details,
                           overall_avg=overall_avg)

# ------------------------------------------------------------------------------
# Entry
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True, port=5004, use_reloader=False)