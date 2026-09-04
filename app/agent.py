import json
from datetime import datetime, timezone

from .db import (
    agent_run,
    get_setting,
    increment_provider,
    jobs_get,
    jobs_set,
    jobs_update,
    linkedin_duplicate_image,
    linkedin_posts_latest,
    linkedin_posts_push,
    lock,
    now_iso,
    set_setting,
    unlock,
)
from .jobs import Sources
from .ai import AI
from .telegram import Telegram
from .image import Image
from .linkedin import LinkedIn

TOPICS = [
    "AI", "AI Agents", "Web Development", "React", "Next.js", "Node.js",
    "TypeScript", "Python", "APIs", "Open Source", "Software Engineering",
    "Developer Productivity", "Automation", "Cloud", "Career Growth",
    "AI + Web Development", "Modern Web Architecture",
]


class Agent:
    def __init__(self, c):
        self.c = c
        self.t = Telegram(c)
        self.ai = AI(c)

    def paused(self):
        return str(get_setting("paused", "false")).lower() == "true"

    def career(self):
        ok, lid = lock("career", self.c.career_interval * 60)
        if not ok:
            return {"status": "SKIPPED", "reason": "lock held"}
        try:
            if self.paused():
                return {"status": "PAUSED"}
            jobs = Sources(self.c).discover()
            new = strong = 0
            for job in jobs:
                fingerprint = job["fingerprint"]
                if jobs_get(fingerprint):
                    continue
                try:
                    scored = self.ai.score(job, self.c.profile)
                    score = max(0, min(100, int(scored.get("score", 0))))
                    reason = str(scored.get("reason", ""))
                    increment_provider("openrouter")
                except Exception:
                    score = 0
                    reason = "AI scoring unavailable; rejected safely"
                status = "MATCHED" if score >= self.c.threshold else "REJECTED"
                record = {
                    **job,
                    "id": fingerprint,
                    "skills": job.get("skills", []),
                    "match_score": score,
                    "match_reason": reason,
                    "status": status,
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                }
                jobs_set(fingerprint, record)
                new += 1
                if score >= self.c.threshold:
                    strong += 1
                    msg = f"""🔥 NEW JOB MATCH

💼 Role:
{job['title']}

🏢 Company:
{job['company'] or 'Not disclosed'}

🌍 Work Type:
Remote

📍 Location:
{job['location'] or 'Not specified'}

⭐ AI MATCH: {score}/100

🛠 Skills:
{', '.join(job['skills']) if job['skills'] else 'Not specified'}

💰 Salary:
{job['salary'] or 'Not disclosed'}

🧑‍💻 Experience:
{job['experience'] or 'Not specified'}

📅 Posted:
{job['posted_at'] or 'Not specified'}

🧠 WHY THIS MATCHES:
{reason or 'No additional explanation provided'}

🔗 APPLY:
{job['url']}

SOURCE: {job['source']}"""
                    try:
                        self.t.send(msg, [[
                            {"text": "APPLY", "url": job["url"]},
                            {"text": "SAVE", "callback_data": f"save:{fingerprint}"},
                            {"text": "IGNORE", "callback_data": f"ignore:{fingerprint}"},
                        ]])
                        jobs_update(fingerprint, {"status": "SENT", "updated_at": now_iso()})
                    except Exception:
                        pass
            metrics = {"found": len(jobs), "new": new, "strong": strong}
            agent_run("career", "SUCCESS", metrics=metrics)
            set_setting("last_career_scan", now_iso())
            return {"status": "SUCCESS", **metrics}
        except Exception as exc:
            agent_run("career", "FAILED", error=str(exc))
            raise
        finally:
            unlock("career", lid)

    def linkedin(self):
        ok, lid = lock("linkedin", self.c.linkedin_interval * 60)
        if not ok:
            return {"status": "SKIPPED", "reason": "lock held"}
        try:
            if self.paused() or not self.c.linkedin_enabled:
                return {"status": "PAUSED_OR_DISABLED"}
            posts = linkedin_posts_latest(50)
            published = [p for p in posts if p.get("status") == "PUBLISHED" and p.get("published_at")]
            if published:
                try:
                    last_dt = datetime.fromisoformat(str(published[0]["published_at"]).replace("Z", "+00:00"))
                    if (datetime.now(timezone.utc) - last_dt).total_seconds() < self.c.linkedin_min_interval * 60:
                        return {"status": "RATE_LIMIT_GUARD"}
                except Exception:
                    pass
            used = {p.get("topic") for p in posts[:20]}
            topic = next((x for x in TOPICS if x not in used), TOPICS[0])
            data = self.ai.post(topic)
            caption = str(data.get("caption", "")).strip()
            prompt = str(data.get("image_prompt", "")).strip()
            if not caption or not prompt:
                raise RuntimeError("AI returned incomplete content")
            increment_provider("openrouter")
            image, image_hash, content_type = Image(self.c).generate(prompt)
            if linkedin_duplicate_image(image_hash):
                return {"status": "DUPLICATE_IMAGE"}
            created = now_iso()
            post_key = linkedin_posts_push({
                "topic": topic,
                "caption": caption,
                "image_prompt": prompt,
                "image_hash": image_hash,
                "ai_model": self.c.openrouter_model,
                "status": "QUEUED",
                "created_at": created,
                "updated_at": created,
            })
            post_id = LinkedIn(self.c).publish(caption, image, content_type)
            post_url = LinkedIn(self.c).url(post_id)
            from .db import update
            update(f"linkedin_posts/{post_key}", {
                "post_id": post_id,
                "post_url": post_url,
                "status": "PUBLISHED",
                "published_at": now_iso(),
                "updated_at": now_iso(),
            })
            try:
                self.t.photo(image, f"✅ LINKEDIN POST PUBLISHED\n\n📌 Topic: {topic}\n\n📝 {caption}\n\n🆔 Post ID: {post_id}\n🔗 {post_url or 'Not available'}")
            except Exception:
                pass
            set_setting("last_linkedin_post", now_iso())
            return {"status": "SUCCESS", "topic": topic, "post_id": post_id}
        except Exception as exc:
            try:
                self.t.send(f"⚠️ LINKEDIN CONTENT CYCLE FAILED\n\nTopic: {topic if 'topic' in locals() else 'unknown'}\nReason: {str(exc)[:500]}\n\nNo unsupported LinkedIn action was attempted.")
            except Exception:
                pass
            agent_run("linkedin", "FAILED", error=str(exc))
            raise
        finally:
            unlock("linkedin", lid)
