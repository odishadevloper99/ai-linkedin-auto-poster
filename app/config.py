import json
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def env(name, default=""):
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip()


def jlist(name):
    raw = env(name, "")
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except Exception:
        return [x.strip() for x in raw.split(",") if x.strip()]


@dataclass(frozen=True)
class Config:
    firebase_database_url: str
    firebase_service_account_json: str
    cron_secret: str
    timezone: str
    threshold: int
    career_interval: int
    linkedin_interval: int
    retries: int
    timeout: int
    openrouter_key: str
    openrouter_model: str
    aicredits_key: str
    aicredits_base_url: str
    aicredits_chat_model: str
    hf_key: str
    hf_model: str
    telegram_token: str
    telegram_chat_id: str
    telegram_admin_id: str
    telegram_webhook_url: str
    telegram_webhook_secret: str
    linkedin_token: str
    linkedin_urn: str
    linkedin_version: str
    linkedin_min_interval: int
    linkedin_enabled: bool
    image_base: str
    image_width: int
    image_height: int
    image_model: str
    aicredits_image_model: str
    image_quality: str
    image_size: str
    remotive_enabled: bool
    remotive_url: str
    arbeitnow_enabled: bool
    arbeitnow_url: str
    profile: dict


def load_config():
    return Config(
        env("FIREBASE_DATABASE_URL", ""),
        env("FIREBASE_SERVICE_ACCOUNT_JSON", ""),
        env("CRON_SECRET", ""),
        env("TIMEZONE", "Asia/Kolkata"),
        int(os.getenv("JOB_MATCH_THRESHOLD", "70")),
        int(os.getenv("CAREER_SCAN_INTERVAL_MINUTES", "30")),
        int(os.getenv("LINKEDIN_POST_INTERVAL_MINUTES", "30")),
        int(os.getenv("MAX_RETRIES", "3")),
        int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60")),
        env("OPENROUTER_API_KEY", ""),
        env("OPENROUTER_MODEL", "openrouter/free"),
        env("AICREDITS_API_KEY", ""),
        env("AICREDITS_BASE_URL", "https://api.aicredits.in/v1").rstrip("/"),
        env("AICREDITS_CHAT_MODEL", "openai/gpt-4o-mini"),
        env("HUGGINGFACE_API_KEY", ""),
        env("HUGGINGFACE_MODEL", ""),
        env("TELEGRAM_BOT_TOKEN", ""),
        env("TELEGRAM_CHAT_ID", ""),
        env("TELEGRAM_ADMIN_USER_ID", ""),
        env("TELEGRAM_WEBHOOK_URL", "") or (env("RENDER_EXTERNAL_URL", "").rstrip("/") + "/telegram/webhook" if env("RENDER_EXTERNAL_URL", "") else ""),
        env("TELEGRAM_WEBHOOK_SECRET", ""),
        env("LINKEDIN_ACCESS_TOKEN", ""),
        env("LINKEDIN_USER_URN", ""),
        env("LINKEDIN_VERSION", "202606"),
        int(os.getenv("LINKEDIN_MIN_POST_INTERVAL_MINUTES", "30")),
        env("LINKEDIN_PUBLISH_ENABLED", "true").lower() == "true",
        env("POLLINATIONS_BASE_URL", "https://image.pollinations.ai/prompt/").rstrip("/") + "/",
        int(os.getenv("POLLINATIONS_WIDTH", "1200")),
        int(os.getenv("POLLINATIONS_HEIGHT", "675")),
        env("POLLINATIONS_MODEL", "zimage"),
        env("AICREDITS_IMAGE_MODEL", "black-forest-labs/flux-2-pro"),
        env("AICREDITS_IMAGE_QUALITY", "standard"),
        env("AICREDITS_IMAGE_SIZE", "1440x810"),
        env("REMOTIVE_ENABLED", "true").lower() == "true",
        env("REMOTIVE_API_URL", "https://remotive.com/api/remote-jobs"),
        env("ARBEITNOW_ENABLED", "true").lower() == "true",
        env("ARBEITNOW_API_URL", "https://www.arbeitnow.com/api/job-board-api"),
        {
            "skills": jlist("PROFILE_SKILLS"),
            "technologies": jlist("PROFILE_TECHNOLOGIES"),
            "experience": env("PROFILE_EXPERIENCE", ""),
            "preferred_roles": jlist("PROFILE_PREFERRED_ROLES"),
            "remote_preference": env("PROFILE_REMOTE_PREFERENCE", "remote"),
            "salary_preference": env("PROFILE_SALARY_PREFERENCE", ""),
            "location_preference": env("PROFILE_LOCATION_PREFERENCE", "India"),
            "portfolio": env("PROFILE_PORTFOLIO", ""),
            "github": env("PROFILE_GITHUB", ""),
            "linkedin": env("PROFILE_LINKEDIN", ""),
            "resume_metadata": env("PROFILE_RESUME_METADATA", ""),
        },
    )
