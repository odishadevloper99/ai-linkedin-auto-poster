from flask import Flask, request, jsonify

from .config import load_config
from .db import (
    application_rows,
    get_setting,
    init,
    jobs_by_status,
    jobs_latest,
    jobs_update,
    linkedin_posts_latest,
    get,
    set_setting,
)
from .agent import Agent
from .telegram import Telegram


def create_app():
    c = load_config()
    app = Flask(__name__)
    firebase_error = None
    try:
        init(c.firebase_database_url, c.firebase_service_account_json)
    except Exception as exc:
        firebase_error = str(exc)
        app.logger.exception("Firebase init failed")

    def auth():
        return bool(c.cron_secret) and request.headers.get("X-Cron-Secret") == c.cron_secret

    @app.get("/")
    def root():
        return jsonify({"service": "AI Career + LinkedIn Automation", "status": "ok"})

    @app.get("/health")
    def health():
        if firebase_error:
            return jsonify({"status": "degraded", "database": "UNHEALTHY", "error": firebase_error[:300]}), 503
        try:
            get("settings/health_probe", None)
            return jsonify({"status": "ok", "database": "HEALTHY"})
        except Exception as exc:
            return jsonify({"status": "degraded", "database": "UNHEALTHY", "error": str(exc)[:300]}), 503

    @app.get("/status")
    def status():
        db_status = "HEALTHY" if not firebase_error else "UNHEALTHY"
        return jsonify({
            "career_agent": "PAUSED" if str(get_setting("paused", "false")).lower() == "true" else "RUNNING",
            "job_scanner": "RUNNING" if str(get_setting("paused", "false")).lower() != "true" else "PAUSED",
            "linkedin_engine": "RUNNING" if str(get_setting("paused", "false")).lower() != "true" and c.linkedin_enabled else "PAUSED_OR_DISABLED",
            "openrouter": "CONFIGURED" if c.openrouter_key else "NOT_CONFIGURED",
            "huggingface": "CONFIGURED" if c.hf_key and c.hf_model else "NOT_CONFIGURED",
            "linkedin": "CONFIGURED" if c.linkedin_token and c.linkedin_urn else "NOT_CONFIGURED",
            "telegram": "CONFIGURED" if c.telegram_token and c.telegram_chat_id else "NOT_CONFIGURED",
            "database": db_status,
            "last_job_scan": get_setting("last_career_scan"),
            "last_linkedin_post": get_setting("last_linkedin_post"),
            "next_cycle_minutes": c.career_interval,
        })

    @app.post("/internal/cron/career")
    def career():
        if not auth():
            return jsonify({"error": "unauthorized"}), 401
        try:
            return jsonify(Agent(c).career())
        except Exception as exc:
            app.logger.exception("CAREER CRON FAILED")
            return jsonify({"status": "FAILED", "error": str(exc)[:500]}), 500

    @app.post("/internal/cron/linkedin")
    def linkedin():
        if not auth():
            return jsonify({"error": "unauthorized"}), 401
        force = request.args.get("force", "").lower() == "true"
        if not force:
            body = request.get_json(silent=True) or {}
            force = body.get("force") is True
        try:
            return jsonify(Agent(c).linkedin(force=force))
        except Exception as exc:
            return jsonify({"status": "FAILED", "error": str(exc)[:500]}), 500

    @app.post("/internal/telegram/set-webhook")
    def telegram_set_webhook():
        if not auth():
            return jsonify({"error": "unauthorized"}), 401
        try:
            return jsonify(Telegram(c).set_webhook())
        except Exception as exc:
            return jsonify({"status": "FAILED", "error": str(exc)[:500]}), 500

    @app.post("/telegram/webhook")
    def webhook():
        if c.telegram_webhook_secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != c.telegram_webhook_secret:
            return jsonify({"error": "unauthorized"}), 401
        payload = request.get_json(silent=True) or {}
        callback = payload.get("callback_query")
        t = Telegram(c)

        if callback:
            uid = callback.get("from", {}).get("id")
            data = callback.get("data", "")
            if t.admin(uid):
                try:
                    action, fingerprint = data.split(":", 1)
                    if action in ("save", "ignore"):
                        new_status = "SAVED" if action == "save" else "IGNORED"
                        jobs_update(fingerprint, {"status": new_status})
                        t.answer(callback.get("id"))
                        t.send(f"Job {new_status.lower()}.")
                except Exception:
                    pass
            return jsonify({"ok": True})

        message = payload.get("message", {})
        uid = message.get("from", {}).get("id")
        text = (message.get("text") or "").strip()
        if not t.admin(uid):
            if text.startswith("/start") or text.startswith("/status"):
                try:
                    t.send(f"🔒 Not authorized.\nYour Telegram ID: {uid}\nSet this exact value as TELEGRAM_ADMIN_USER_ID on Render, then try again.")
                except Exception:
                    pass
            return jsonify({"ok": True})

        if text.startswith("/pause"):
            set_setting("paused", "true")
            t.send("⏸ Agent paused. Autonomous external actions are disabled.")
        elif text.startswith("/resume"):
            set_setting("paused", "false")
            t.send("▶️ Agent resumed.")
        elif text.startswith("/status") or text.startswith("/health"):
            t.send(str(status().get_json()))
        elif text.startswith("/topjobs"):
            rows = [x for x in jobs_latest(100) if x.get("status") in ("MATCHED", "SENT", "SAVED")]
            rows = sorted(rows, key=lambda x: x.get("match_score", 0), reverse=True)[:10]
            t.send("\n".join(f"⭐ {x.get('match_score', 0)}/100 | {x.get('title')} | {x.get('company')}\n{x.get('url')}" for x in rows) or "No strong matches yet.")
        elif text.startswith("/jobs"):
            rows = jobs_latest(10)
            t.send("\n".join(f"{x.get('match_score', 0)}/100 {x.get('title')} — {x.get('company')} [{x.get('status')}]" for x in rows) or "No jobs.")
        elif text.startswith("/saved"):
            rows = jobs_by_status("SAVED", 20)
            t.send("\n".join(f"{x.get('title')} — {x.get('company')}\n{x.get('url')}" for x in rows) or "No saved jobs.")
        elif text.startswith("/applied"):
            rows = application_rows(20)
            t.send("\n".join(f"{x.get('title', x.get('job_title', 'Unknown'))} — {x.get('company', '')} [{x.get('status', '')}]" for x in rows) or "No applications.")
        elif text.startswith("/ignored"):
            rows = jobs_by_status("IGNORED", 20)
            t.send("\n".join(f"{x.get('title')} — {x.get('company')}" for x in rows) or "No ignored jobs.")
        elif text.startswith("/posts") or text.startswith("/lastpost"):
            rows = linkedin_posts_latest(10)
            t.send("\n".join(f"{x.get('topic')} [{x.get('status')}] {x.get('post_url') or ''}" for x in rows) or "No posts.")
        elif text.startswith("/stats"):
            rows = jobs_latest(100000)
            strong = sum(1 for x in rows if int(x.get("match_score", 0)) >= c.threshold)
            sent = sum(1 for x in rows if x.get("status") == "SENT")
            t.send(f"Jobs: {len(rows)}\nStrong: {strong}\nSent: {sent}")
        elif text.startswith("/start"):
            t.send("🤖 AI Career Agent ready. Use /status, /jobs, /topjobs, /posts, /pause, /resume.")
        return jsonify({"ok": True})

    return app


app = create_app()
