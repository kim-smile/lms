from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from sqlalchemy import or_, func
from helpers.auth import login_required
from models import db, User, Message

bp = Blueprint("messages", __name__, url_prefix="/messages")

@bp.get("/", endpoint="home")
@login_required
def page():
    uid = g.user.id
    tab = request.args.get("tab", "inbox")
    q = (request.args.get("q") or "").strip()

    base_inbox = db.session.query(Message).filter(Message.receiver_id == uid)
    base_sent = db.session.query(Message).filter(Message.sender_id == uid)

    if q:
        like = f"%{q}%"
        base_inbox = (
            base_inbox.join(User, Message.sender_id == User.id).filter(
                or_(Message.title.like(like), Message.body.like(like), User.name.like(like))
            )
        )
        base_sent = (
            base_sent.join(User, Message.receiver_id == User.id).filter(
                or_(Message.title.like(like), Message.body.like(like), User.name.like(like))
            )
        )

    inbox = base_inbox.order_by(Message.read_at.is_(None).desc(), Message.created_at.desc()).all()
    sent = base_sent.order_by(Message.created_at.desc()).all()
    users = db.session.query(User).filter(User.id != uid).order_by(User.name.asc()).all()

    unread_cnt = db.session.scalar(
        db.select(func.count(Message.id)).where(
            Message.receiver_id == uid, Message.read_at.is_(None)
        )
    ) or 0

    return render_template("messages.html", tab=tab, q=q, inbox=inbox, sent=sent, users=users, unread_cnt=unread_cnt)

@bp.get("/<int:msg_id>")
@login_required
def detail(msg_id: int):
    uid = g.user.id
    m = db.session.get(Message, msg_id)
    if not m or (m.sender_id != uid and m.receiver_id != uid):
        abort(404)
    if m.receiver_id == uid and m.read_at is None:
        from datetime import datetime
        m.read_at = datetime.utcnow()
        db.session.commit()
    return render_template("message_detail.html", m=m)

@bp.post("/send")
@login_required
def send():
    uid = g.user.id
    to_id = request.form.get("to_id")
    title = (request.form.get("title") or "").strip()
    body = (request.form.get("body") or "").strip()
    if not to_id or not to_id.isdigit() or not title:
        flash("받는 사람과 제목은 필수입니다.", "error")
        return redirect(url_for("messages.page", tab="compose"))

    msg = Message(sender_id=uid, receiver_id=int(to_id), title=title, body=body)
    db.session.add(msg)
    db.session.commit()
    flash("메시지를 보냈습니다.", "success")
    return redirect(url_for("messages.page", tab="sent"))

@bp.post("/reply/<int:msg_id>")
@login_required
def reply(msg_id: int):
    uid = g.user.id
    src = db.session.get(Message, msg_id)
    if not src or (src.sender_id != uid and src.receiver_id != uid):
        abort(404)
    to_id = src.sender_id if src.receiver_id == uid else src.receiver_id
    title = (request.form.get("title") or f"Re: {src.title}").strip()
    body = (request.form.get("body") or "").strip()
    if not title:
        flash("제목은 필수입니다.", "error")
        return redirect(url_for("messages.detail", msg_id=msg_id))
    msg = Message(sender_id=uid, receiver_id=to_id, title=title, body=body)
    db.session.add(msg)
    db.session.commit()
    flash("답장을 보냈습니다.", "success")
    return redirect(url_for("messages.page", tab="sent"))