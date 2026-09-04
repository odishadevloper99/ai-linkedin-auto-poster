import json
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def jlist(name):
    raw = os.getenv(name, "")
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
        os.getenv("FIREBASE_DATABASE_URL", ""),
        os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", ""),
        os.getenv("CRON_SECRET", ""),
        os.getenv("TIMEZONE", "Asia/Kolkata"),
        int(os.getenv("JOB_MATCH_THRESHOLD", "70")),
        int(os.getenv("CAREER_SCAN_INTERVAL_MINUTES", "30")),
        int(os.getenv("LINKEDIN_POST_INTERVAL_MINUTES", "30")),
        int(os.getenv("MAX_RETRIES", "3")),
        int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60")),
        os.getenv("OPENROUTER_API_KEY", ""),
        os.getenv("OPENROUTER_MODEL", "openrouter/free"),
        os.getenv("AICREDITS_API_KEY", ""),
        os.getenv("AICREDITS_BASE_URL", "https://api.aicredits.in/v1").rstrip("/"),
        os.getenv("AICREDITS_CHAT_MODEL", "openai/gpt-4o-mini"),
        os.getenv("HUGGINGFACE_API_KEY", ""),
        os.getenv("HUGGINGFACE_MODEL", ""),
        os.getenv("TELEGRAM_BOT_TOKEN", ""),
        os.getenv("TELEGRAM_CHAT_ID", ""),
        os.getenv("TELEGRAM_ADMIN_USER_ID", ""),
        os.getenv("TELEGRAM_WEBHOOK_URL", "") or (os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/") + "/telegram/webhook" if os.getenv("RENDER_EXTERNAL_URL", "") else ""),
        os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
        os.getenv("LINKEDIN_ACCESS_TOKEN", ""),
        os.getenv("LINKEDIN_USER_URN", ""),
        os.getenv("LINKEDIN_VERSION", "202606"),
        int(os.getenv("LINKEDIN_MIN_POST_INTERVAL_MINUTES", "30")),
        os.getenv("LINKEDIN_PUBLISH_ENABLED", "true").lower() == "true",
        os.getenv("POLLINATIONS_BASE_URL", "https://image.pollinations.ai/prompt/").rstrip("/") + "/",
        int(os.getenv("POLLINATIONS_WIDTH", "1200")),
        int(os.getenv("POLLINATIONS_HEIGHT", "675")),
        os.getenv("POLLINATIONS_MODEL", "zimage"),
        os.getenv("AICREDITS_IMAGE_MODEL", "black-forest-labs/flux-2-pro"),
        os.getenv("AICREDITS_IMAGE_QUALITY", "standard"),
        os.getenv("AICREDITS_IMAGE_SIZE", "1792x1024"),
        os.getenv("REMOTIVE_ENABLED", "true").lower() == "true",
        os.getenv("REMOTIVE_API_URL", "https://remotive.com/api/remote-jobs"),
        os.getenv("ARBEITNOW_ENABLED", "true").lower() == "true",
        os.getenv("ARBEITNOW_API_URL", "https://www.arbeitnow.com/api/job-board-api"),
        {
            "skills": jlist("PROFILE_SKILLS"),
            "technologies": jlist("PROFILE_TECHNOLOGIES"),
            "experience": os.getenv("PROFILE_EXPERIENCE", ""),
            "preferred_roles": jlist("PROFILE_PREFERRED_ROLES"),
            "remote_preference": os.getenv("PROFILE_REMOTE_PREFERENCE", "remote"),
            "salary_preference": os.getenv("PROFILE_SALARY_PREFERENCE", ""),
            "location_preference": os.getenv("PROFILE_LOCATION_PREFERENCE", "India"),
            "portfolio": os.getenv("PROFILE_PORTFOLIO", ""),
            "github": os.getenv("PROFILE_GITHUB", ""),
            "linkedin": os.getenv("PROFILE_LINKEDIN", ""),
            "resume_metadata": os.getenv("PROFILE_RESUME_METADATA", ""),
        },
    )
