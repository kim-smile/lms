from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from sqlalchemy import or_
from helpers.auth import login_required, roles_required
from helpers.utils import _save_upload
from models import (
    db, User, MentoringTeam, MentoringTeamMember, MentoringReport,
    Project, ProjectTask, Competition, CompetitionEntry
)

bp = Blueprint("mentoring", __name__, url_prefix="/mentoring")

@bp.get("/", endpoint="home")  # ✅ 엔드포인트: mentoring.home
@login_required
def home():
    uid = g.user.id
    tab = (request.args.get("tab") or "reports").strip().lower()
    if tab not in {"reports", "teams", "projects", "competitions", "github"}:
        tab = "reports"

    # 내가 속한 팀 및 내가 소유한 팀
    my_teams = (
        db.session.query(MentoringTeam)
        .join(MentoringTeamMember, MentoringTeamMember.team_id == MentoringTeam.id)
        .filter(MentoringTeamMember.user_id == uid)
        .all()
    )
    teams_owned = db.session.query(MentoringTeam).filter_by(owner_user_id=uid).all()
    team_ids = [t.id for t in my_teams]

    # 내 보고서
    my_reports = (
        db.session.query(MentoringReport)
        .filter_by(author_user_id=uid)
        .order_by(MentoringReport.created_at.desc())
        .all()
    )

    # 내 프로젝트(내가 소유 or 내 팀의 프로젝트)
    conds = [Project.owner_user_id == uid]
    if team_ids:
        conds.append(Project.team_id.in_(team_ids))
    my_projects = (
        db.session.query(Project)
        .filter(or_(*conds))
        .order_by(Project.created_at.desc())
        .all()
    )

    # 공모전(마감일 오름차순, 마감일 없는 것은 뒤로)
    comps = (
        db.session.query(Competition)
        .order_by(Competition.apply_deadline.is_(None), Competition.apply_deadline.asc())
        .all()
    )

    # 내가 낸 공모전 참가(개인 or 내 팀)
    entry_conds = [CompetitionEntry.applicant_user_id == uid]
    if team_ids:
        entry_conds.append(CompetitionEntry.team_id.in_(team_ids))
    my_entries = (
        db.session.query(CompetitionEntry)
        .filter(or_(*entry_conds))
        .order_by(CompetitionEntry.created_at.desc())
        .all()
    )

    return render_template(
        "mentoring.html",
        tab=tab,
        my_reports=my_reports,
        my_teams=my_teams,
        teams_owned=teams_owned,
        my_projects=my_projects,
        comps=comps,
        my_entries=my_entries,
    )

@bp.post("/reports/new")
@login_required
def report_new():
    uid = g.user.id
    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    team_id = request.form.get("team_id")
    team_id_int = int(team_id) if team_id and team_id.isdigit() else None

    file = request.files.get("file")
    file_url = _save_upload(file, prefix=f"report_u{uid}") if file else None

    if not title:
        flash("제목은 필수입니다.", "error")
        return redirect(url_for("mentoring.home", tab="reports"))

    r = MentoringReport(
        author_user_id=uid,
        team_id=team_id_int,
        title=title,
        content=content,
        file_url=file_url,
    )
    db.session.add(r)
    db.session.commit()
    flash("보고서가 등록되었습니다.", "success")
    return redirect(url_for("mentoring.home", tab="reports"))

@bp.post("/teams/new")
@login_required
def team_new():
    uid = g.user.id
    name = (request.form.get("name") or "").strip()
    is_solo = bool(request.form.get("is_solo"))
    if not name:
        flash("팀 이름은 필수입니다.", "error")
        return redirect(url_for("mentoring.home", tab="teams"))

    team = MentoringTeam(name=name, owner_user_id=uid, is_solo=is_solo)
    db.session.add(team)
    db.session.flush()  # team.id 확보
    db.session.add(MentoringTeamMember(team_id=team.id, user_id=uid, role="leader"))
    db.session.commit()
    flash("팀이 생성되었습니다.", "success")
    return redirect(url_for("mentoring.home", tab="teams"))

@bp.post("/teams/join")
@login_required
def team_join():
    uid = g.user.id
    team_id = request.form.get("team_id")
    if not team_id or not team_id.isdigit():
        flash("팀 ID가 올바르지 않습니다.", "error")
        return redirect(url_for("mentoring.home", tab="teams"))

    team_id_int = int(team_id)
    exists = (
        db.session.query(MentoringTeamMember)
        .filter_by(team_id=team_id_int, user_id=uid)
        .first()
    )
    if exists:
        flash("이미 해당 팀에 속해 있습니다.", "error")
        return redirect(url_for("mentoring.home", tab="teams"))

    db.session.add(MentoringTeamMember(team_id=team_id_int, user_id=uid, role="member"))
    db.session.commit()
    flash("팀에 참여했습니다.", "success")
    return redirect(url_for("mentoring.home", tab="teams"))

@bp.post("/projects/new")
@login_required
def project_new():
    uid = g.user.id
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    team_id = request.form.get("team_id")
    github = (request.form.get("github") or "").strip()
    team_id_int = int(team_id) if team_id and team_id.isdigit() else None

    if not title:
        flash("프로젝트 제목은 필수입니다.", "error")
        return redirect(url_for("mentoring.home", tab="projects"))

    p = Project(
        title=title,
        description=description,
        team_id=team_id_int,
        owner_user_id=uid if not team_id_int else None,
        github_repo_url=github or None,
    )
    db.session.add(p)
    db.session.commit()
    flash("프로젝트가 생성되었습니다.", "success")
    return redirect(url_for("mentoring.home", tab="projects"))

@bp.post("/tasks/new")
@login_required
def task_new():
    from helpers.utils import _parse_dt
    project_id = request.form.get("project_id")
    title = (request.form.get("title") or "").strip()
    due_at = request.form.get("due_at")  # 'YYYY-MM-DD HH:MM'
    assignee_id = request.form.get("assignee_id")

    if not project_id or not project_id.isdigit() or not title:
        flash("프로젝트와 제목은 필수입니다.", "error")
        return redirect(url_for("mentoring.home", tab="projects"))

    dt = _parse_dt(due_at)
    if due_at and not dt:
        flash("마감 형식은 YYYY-MM-DD HH:MM 입니다.", "error")
        return redirect(url_for("mentoring.home", tab="projects"))

    assignee_id_int = int(assignee_id) if assignee_id and assignee_id.isdigit() else None

    t = ProjectTask(
        project_id=int(project_id),
        title=title,
        due_at=dt,
        assignee_user_id=assignee_id_int,
    )
    db.session.add(t)
    db.session.commit()
    flash("작업이 추가되었습니다.", "success")
    return redirect(url_for("mentoring.home", tab="projects"))

@bp.post("/competitions/new")
@roles_required("admin", "instructor")
def comp_new():
    from helpers.utils import _parse_dt
    title = (request.form.get("title") or "").strip()
    host = (request.form.get("host") or "").strip()
    url_ = (request.form.get("url") or "").strip()
    deadline = request.form.get("apply_deadline")

    dt = None
    if deadline:
        dt = _parse_dt(deadline)
        if not dt:
            flash("마감 형식은 YYYY-MM-DD HH:MM 입니다.", "error")
            return redirect(url_for("mentoring.home", tab="competitions"))

    if not title:
        flash("공모전 제목은 필수입니다.", "error")
        return redirect(url_for("mentoring.home", tab="competitions"))

    c = Competition(title=title, host=host or None, url=url_ or None, apply_deadline=dt)
    db.session.add(c)
    db.session.commit()
    flash("공모전이 등록되었습니다.", "success")
    return redirect(url_for("mentoring.home", tab="competitions"))

@bp.post("/competitions/apply")
@login_required
def comp_apply():
    uid = g.user.id
    competition_id = request.form.get("competition_id")
    team_id = request.form.get("team_id")
    project_id = request.form.get("project_id")

    if not competition_id or not competition_id.isdigit():
        flash("공모전 ID가 올바르지 않습니다.", "error")
        return redirect(url_for("mentoring.home", tab="competitions"))

    entry = CompetitionEntry(
        competition_id=int(competition_id),
        team_id=int(team_id) if team_id and team_id.isdigit() else None,
        applicant_user_id=uid,
        project_id=int(project_id) if project_id and project_id.isdigit() else None,
        status="submitted",
    )
    db.session.add(entry)
    db.session.commit()
    flash("공모전에 신청했습니다.", "success")
    return redirect(url_for("mentoring.home", tab="competitions"))