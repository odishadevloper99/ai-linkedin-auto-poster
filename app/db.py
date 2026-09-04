import json
import time
import uuid
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, db as firebase_db

_APP = None


def init(database_url: str, credentials_json: str):
    global _APP
    if _APP is not None:
        return
    if not database_url:
        raise RuntimeError("FIREBASE_DATABASE_URL is required")
    if not credentials_json:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is required")
    try:
        info = json.loads(credentials_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc
    cred = credentials.Certificate(info)
    _APP = firebase_admin.initialize_app(cred, {"databaseURL": database_url})


def ref(path=""):
    if _APP is None:
        raise RuntimeError("Firebase database is not initialized")
    return firebase_db.reference(path)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get(path, default=None):
    value = ref(path).get()
    return default if value is None else value


def _clean_firebase_value(value):
    if isinstance(value, dict):
        return {
            str(k): _clean_firebase_value(v)
            for k, v in value.items()
            if v is not None
        }
    if isinstance(value, list):
        return [_clean_firebase_value(v) for v in value if v is not None]
    return value


def set_value(path, value):
    cleaned = _clean_firebase_value(value)
    ref(path).set(cleaned)
    return cleaned


def update(path, value):
    cleaned = _clean_firebase_value(value)
    ref(path).update(cleaned)
    return cleaned


def push(path, value):
    child = ref(path).push()
    child.set(value)
    return child.key


def delete(path):
    ref(path).delete()


def jobs_get(fingerprint):
    return get(f"jobs/{fingerprint}")


def jobs_set(fingerprint, value):
    return set_value(f"jobs/{fingerprint}", value)


def jobs_update(fingerprint, value):
    return update(f"jobs/{fingerprint}", value)


def jobs_all():
    data = get("jobs", {}) or {}
    return list(data.values()) if isinstance(data, dict) else []


def jobs_latest(limit=10):
    rows = jobs_all()
    return sorted(rows, key=lambda x: x.get("created_at", ""), reverse=True)[:limit]


def jobs_by_status(status, limit=20):
    rows = [x for x in jobs_all() if x.get("status") == status]
    return sorted(rows, key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)[:limit]


def linkedin_posts_all():
    data = get("linkedin_posts", {}) or {}
    return list(data.values()) if isinstance(data, dict) else []


def linkedin_posts_latest(limit=20):
    return sorted(linkedin_posts_all(), key=lambda x: x.get("created_at", ""), reverse=True)[:limit]


def linkedin_posts_push(value):
    return push("linkedin_posts", value)


def linkedin_duplicate_image(image_hash):
    data = ref("linkedin_posts").order_by_child("image_hash").equal_to(image_hash).get()
    return bool(data)


def application_rows(limit=20):
    data = get("applications", {}) or {}
    rows = list(data.values()) if isinstance(data, dict) else []
    return sorted(rows, key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)[:limit]


def agent_run(agent, status, metrics=None, error=None):
    value = {"agent": agent, "status": status, "finished_at": now_iso()}
    if metrics is not None:
        value["metrics"] = metrics
    if error:
        value["error"] = str(error)[:1000]
    return push("agent_runs", value)


def log_event(path, value):
    return push(path, value)


def get_setting(key, default=None):
    return get(f"settings/{key}", default)


def set_setting(key, value):
    return set_value(f"settings/{key}", value)


def increment_provider(provider):
    path = f"provider_usage/{provider}/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    current = get(path, 0) or 0
    set_value(path, int(current) + 1)


def lock(name, ttl=1800):
    lock_ref = ref(f"locks/{name}")
    lock_id = str(uuid.uuid4())
    now = int(time.time())
    expires = now + int(ttl)

    def txn(current):
        if not current or int(current.get("expires_at", 0)) <= now:
            return {"lock_id": lock_id, "created_at": now, "expires_at": expires}
        return current

    result = lock_ref.transaction(txn)
    return bool(result and result.get("lock_id") == lock_id), lock_id


def unlock(name, lock_id):
    lock_ref = ref(f"locks/{name}")

    def txn(current):
        if current and current.get("lock_id") == lock_id:
            # Firebase transactions reject None as a whole-value result.
            # An empty object is a valid unlocked lock and is treated as
            # available by lock(), while preserving atomic transaction semantics.
            return {}
        return current

    lock_ref.transaction(txn)
