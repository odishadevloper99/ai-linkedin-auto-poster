#!/usr/bin/env python3
"""
AI LinkedIn Auto-Poster
- Scheduled mode: python main.py
- Manual mode:   python main.py --postnow
- Status mode:   python main.py --status

All credentials are read from environment variables.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("linkedin-poster")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
POLLINATIONS_BASE = os.getenv(
    "POLLINATIONS_BASE_URL",
    "https://image.pollinations.ai/prompt/",
).rstrip("/") + "/"

# Image quality settings for Pollinations. Overridable via env vars.
POLLINATIONS_WIDTH = os.getenv("POLLINATIONS_WIDTH", "1200")
POLLINATIONS_HEIGHT = os.getenv("POLLINATIONS_HEIGHT", "675")
POLLINATIONS_MODEL = os.getenv("POLLINATIONS_MODEL", "flux")

LINKEDIN_ASSET_URL = "https://api.linkedin.com/v2/assets?action=registerUpload"
LINKEDIN_UGC_URL = "https://api.linkedin.com/v2/ugcPosts"
TELEGRAM_URL = "https://api.telegram.org/bot{}/{}"

TOPICS = [
    "AI and everyday productivity",
    "Generative AI for developers",
    "AI agents and automation",
    "Python development",
    "Open source software",
    "Cybersecurity awareness",
    "Cloud computing",
    "Developer tools",
    "Software engineering best practices",
    "AI-assisted coding",
    "Future of technology",
    "Building useful AI products",
]


class ConfigError(RuntimeError):
    pass


class APIError(RuntimeError):
    pass


def env(name: str, required: bool = True, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ConfigError(f"Missing environment variable: {name}")
    return value or ""


def load_config() -> dict[str, str]:
    cfg = {
        "linkedin_client_id": env("LINKEDIN_CLIENT_ID"),
        "linkedin_client_secret": env("LINKEDIN_CLIENT_SECRET"),
        "linkedin_access_token": env("LINKEDIN_ACCESS_TOKEN"),
        "linkedin_user_urn": env("LINKEDIN_USER_URN"),
        "openrouter_api_key": env("OPENROUTER_API_KEY"),
        "openrouter_model": env(
            "OPENROUTER_MODEL",
            required=False,
            default="openrouter/free",
        ),
        "telegram_bot_token": env("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": env("TELEGRAM_CHAT_ID"),
        "max_retries": env("MAX_RETRIES", required=False, default="3"),
        "post_timezone": env("POST_TIMEZONE", required=False, default="UTC"),
    }
    return cfg


def safe_error(exc: Exception) -> str:
    msg = str(exc)
    secret_names = [
        "LINKEDIN_CLIENT_SECRET",
        "LINKEDIN_ACCESS_TOKEN",
        "OPENROUTER_API_KEY",
        "TELEGRAM_BOT_TOKEN",
    ]
    for name in secret_names:
        value = os.getenv(name)
        if value:
            msg = msg.replace(value, "***REDACTED***")
    return msg[:1200]


def request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    data: bytes | None = None,
    timeout: tuple[int, int] = (15, 60),
    max_retries: int = 3,
) -> requests.Response:
    retry_statuses = {408, 429, 500, 502, 503, 504}
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=json_body,
                data=data,
                timeout=timeout,
            )
            if response.status_code not in retry_statuses:
                return response
            last_exc = APIError(
                f"{method} {url} returned HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
        except requests.RequestException as exc:
            last_exc = exc

        if attempt < max_retries - 1:
            delay = 2 ** attempt
            log.warning("Transient failure; retrying in %ss", delay)
            time.sleep(delay)

    raise APIError(safe_error(last_exc or RuntimeError("request failed")))


def telegram_send(cfg: dict[str, str], message: str) -> None:
    url = TELEGRAM_URL.format(cfg["telegram_bot_token"], "sendMessage")
    try:
        response = requests.post(
            url,
            json={
                "chat_id": cfg["telegram_chat_id"],
                "text": message,
                "disable_web_page_preview": False,
            },
            timeout=(10, 20),
        )
        response.raise_for_status()
    except Exception as exc:
        log.error("Telegram notification failed: %s", safe_error(exc))


def telegram_send_photo(cfg: dict[str, str], image_bytes: bytes, caption: str = "") -> None:
    bot_token = cfg["telegram_bot_token"]
    chat_id = cfg["telegram_chat_id"]
    url = TELEGRAM_URL.format(bot_token, "sendPhoto")
    try:
        response = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption[:1024]},
            files={"photo": ("linkedin-image.jpg", image_bytes, "image/jpeg")},
            timeout=(15, 60),
        )
        if response.status_code != 200:
            raise APIError(f"Telegram photo HTTP {response.status_code}: {response.text[:500]}")
    except Exception as exc:
        log.error("Telegram photo send failed: %s", safe_error(exc))


def generate_topic() -> str:
    # Optional seed from previous local run is deliberately not required.
    return random.choice(TOPICS)


def openrouter_chat(
    cfg: dict[str, str],
    prompt: str,
    *,
    system: str,
) -> str:
    headers = {
        "Authorization": f"Bearer {cfg['openrouter_api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "AI LinkedIn Auto-Poster",
    }
    body = {
        "model": cfg["openrouter_model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.85,
        "stream": False,
    }

    response = request_with_retry(
        "POST",
        OPENROUTER_URL,
        headers=headers,
        json_body=body,
        timeout=(15, 90),
        max_retries=int(cfg["max_retries"]),
    )
    if not response.ok:
        raise APIError(
            f"OpenRouter HTTP {response.status_code}: {response.text[:1000]}"
        )

    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise APIError(f"OpenRouter returned an invalid response: {response.text[:1000]}") from exc

    if isinstance(content, list):
        content = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    content = str(content).strip()
    if not content:
        raise APIError("OpenRouter returned an empty response.")
    return content


def clean_caption(text: str) -> str:
    text = re.sub(r"^```(?:text|markdown)?\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"\s*```$", "", text.strip())
    text = re.sub(r"^(caption|linkedin caption)\s*:\s*", "", text.strip(), flags=re.I)
    return text.strip()[:2950]


def generate_caption(cfg: dict[str, str], topic: str) -> str:
    system = (
        "You are an expert LinkedIn content writer. Write concise, useful, "
        "human-sounding posts for a technology-focused personal profile. "
        "Never claim personal achievements that were not provided. "
        "Never mention being an AI. Avoid clickbait and corporate fluff."
    )
    prompt = f"""
Create one original LinkedIn post about this topic:

{topic}

Requirements:
- Start with a strong but natural hook.
- Give practical insight a developer or technology professional can use.
- Use short paragraphs for mobile readability.
- Use a few relevant emojis only when helpful.
- End with 3 to 7 relevant hashtags.
- Do not invent statistics, clients, credentials, or personal experiences.
- Do not use markdown tables.
- Return only the final post text.
- Keep it under 1,300 characters.
"""
    return clean_caption(openrouter_chat(cfg, prompt, system=system))


def generate_image_prompt(cfg: dict[str, str], topic: str) -> str:
    system = (
        "You create prompts for professional editorial technology illustrations. "
        "Prompts should produce clean, modern, realistic or premium conceptual "
        "visuals without logos, copyrighted characters, or large blocks of text."
    )
    prompt = f"""
Create one detailed image-generation prompt for a LinkedIn post about:

{topic}

The image should:
- be professional and visually striking;
- have a landscape composition;
- communicate the topic immediately;
- use a modern technology/editorial aesthetic;
- be highly detailed, sharp focus, high resolution, professional photography or
  premium digital art quality;
- contain no written paragraphs, logos, watermarks, or brand marks.

Return only the image prompt.
"""
    return openrouter_chat(cfg, prompt, system=system).replace("\n", " ").strip()


def generate_image(cfg: dict[str, str], prompt: str) -> tuple[bytes, str]:
    query = {
        "width": POLLINATIONS_WIDTH,
        "height": POLLINATIONS_HEIGHT,
        "model": POLLINATIONS_MODEL,
        "nologo": "true",
        "enhance": "true",
        "seed": str(random.randint(1, 999_999)),
    }
    url = POLLINATIONS_BASE + quote(prompt, safe="") + "?" + urlencode(query)
    response = request_with_retry(
        "GET",
        url,
        headers={"Accept": "image/avif,image/webp,image/png,image/jpeg,*/*"},
        timeout=(15, 180),
        max_retries=int(cfg["max_retries"]),
    )
    if not response.ok:
        raise APIError(
            f"Image API HTTP {response.status_code}: {response.text[:500]}"
        )

    content_type = response.headers.get("Content-Type", "").lower()
    if not content_type.startswith("image/"):
        raise APIError(
            f"Image API returned non-image content type: {content_type or 'unknown'}"
        )
    if not response.content:
        raise APIError("Image API returned empty image bytes.")

    extension = "jpg"
    if "png" in content_type:
        extension = "png"
    elif "webp" in content_type:
        extension = "webp"
    elif "gif" in content_type:
        extension = "gif"

    return response.content, extension


def linkedin_headers(cfg: dict[str, str], *, rest: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {cfg['linkedin_access_token']}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if rest:
        # Current LinkedIn REST APIs require a YYYYMM LinkedIn-Version header.
        headers["Linkedin-Version"] = os.getenv(
            "LINKEDIN_VERSION",
            "202604",
        )
    return headers


def linkedin_register_upload(cfg: dict[str, str]) -> tuple[str, str]:
    body = {
        "registerUploadRequest": {
            "owner": cfg["linkedin_user_urn"],
            "recipes": [
                "urn:li:digitalmediaRecipe:feedshare-image"
            ],
            "serviceRelationships": [
                {
                    "identifier": "urn:li:userGeneratedContent",
                    "relationshipType": "OWNER",
                }
            ],
            "supportedUploadMechanism": [
                "SYNCHRONOUS_UPLOAD"
            ],
        }
    }

    # Keep compatibility with the user's requested v2 Assets endpoint.
    response = request_with_retry(
        "POST",
        LINKEDIN_ASSET_URL,
        headers=linkedin_headers(cfg),
        json_body=body,
        timeout=(15, 60),
        max_retries=int(cfg["max_retries"]),
    )
    if not response.ok:
        raise APIError(
            f"LinkedIn registerUpload HTTP {response.status_code}: {response.text[:1200]}"
        )

    payload = response.json()
    value = payload.get("value", {})
    asset = value.get("asset")
    upload_url = (
        value.get("uploadMechanism", {})
        .get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
        .get("uploadUrl")
    )
    if not asset or not upload_url:
        raise APIError(f"LinkedIn upload registration missing asset/uploadUrl: {response.text[:1200]}")
    return asset, upload_url


def linkedin_upload_image(
    cfg: dict[str, str],
    upload_url: str,
    image_bytes: bytes,
    extension: str,
) -> None:
    content_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }
    response = request_with_retry(
        "PUT",
        upload_url,
        headers={
            "Content-Type": content_types.get(extension, "application/octet-stream"),
        },
        data=image_bytes,
        timeout=(15, 120),
        max_retries=int(cfg["max_retries"]),
    )
    if not (200 <= response.status_code < 300):
        raise APIError(
            f"LinkedIn image upload HTTP {response.status_code}: {response.text[:1000]}"
        )


def linkedin_create_post_v2(cfg: dict[str, str], caption: str, asset: str) -> str:
    """Create an image UGC post using the legacy v2 endpoint specified by the prompt."""
    body = {
        "author": cfg["linkedin_user_urn"],
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": caption},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "description": {"text": "AI-generated visual"},
                        "media": asset,
                        "title": {"text": "AI-generated visual"},
                    }
                ],
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    response = request_with_retry(
        "POST",
        LINKEDIN_UGC_URL,
        headers=linkedin_headers(cfg),
        json_body=body,
        timeout=(15, 60),
        max_retries=int(cfg["max_retries"]),
    )
    log.info(
        "LinkedIn UGC response: HTTP %s | body=%s",
        response.status_code,
        response.text[:1000],
    )

    if response.status_code not in (200, 201):
        raise APIError(
            f"LinkedIn UGC post HTTP {response.status_code}: {response.text[:1500]}"
        )

    post_id = response.headers.get("X-RestLi-Id")
    if not post_id:
        try:
            payload = response.json()
            post_id = payload.get("id")
        except ValueError:
            post_id = None

    if not post_id:
        raise APIError("LinkedIn accepted the request but returned no post ID.")
    return post_id


def linkedin_create_post(cfg: dict[str, str], caption: str, asset: str) -> str:
    return linkedin_create_post_v2(cfg, caption, asset)


def linkedin_post_url(post_id: str) -> str | None:
    """
    LinkedIn's API identifiers are not guaranteed to be directly convertible
    to a public URL. Only return a URL for the common numeric URN/id forms.
    """
    if re.fullmatch(r"\d+", post_id):
        return f"https://www.linkedin.com/feed/update/urn:li:activity:{post_id}/"

    match = re.fullmatch(r"urn:li:activity:(\d+)", post_id)
    if match:
        return f"https://www.linkedin.com/feed/update/urn:li:activity:{match.group(1)}/"

    return None


def status_file() -> Path:
    return Path(os.getenv("STATUS_FILE", ".linkedin_status.json"))


def save_status(result: str, *, topic: str = "", post_id: str = "", error: str = "") -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "topic": topic,
        "post_id": post_id,
        "error": error,
    }
    try:
        status_file().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        log.warning("Could not save local status: %s", safe_error(exc))


def read_status() -> dict[str, Any]:
    try:
        return json.loads(status_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "timestamp": "No local status available",
            "result": "UNKNOWN",
            "topic": "",
            "post_id": "",
            "error": "",
        }


def publish_post(cfg: dict[str, str]) -> str:
    topic = ""
    try:
        topic = generate_topic()
        log.info("Topic: %s", topic)

        caption = generate_caption(cfg, topic)
        log.info("Caption generated (%d chars)", len(caption))

        image_prompt = generate_image_prompt(cfg, topic)
        image_bytes, extension = generate_image(cfg, image_prompt)
        log.info("Image generated (%d bytes)", len(image_bytes))

        asset, upload_url = linkedin_register_upload(cfg)
        linkedin_upload_image(cfg, upload_url, image_bytes, extension)
        log.info("Image uploaded: %s", asset)

        post_id = linkedin_create_post(cfg, caption, asset)
        save_status("SUCCESS", topic=topic, post_id=post_id)

        post_url = linkedin_post_url(post_id)
        lines = [
            "✅ LinkedIn Post Published",
            "",
            "📝 Caption generated successfully",
            "🖼️ Image generated successfully",
            "📤 Image uploaded successfully",
            "🚀 Post published successfully",
            "",
            f"Topic: {topic}",
            f"Post ID: {post_id}",
        ]
        if post_url:
            lines += ["", f"🔗 {post_url}"]
        lines += [
            "",
            f"⏰ {datetime.now(timezone.utc).isoformat()}",
        ]
        telegram_send_photo(cfg, image_bytes, f"✅ LinkedIn Auto Post\n\nTopic: {topic}")
        telegram_send(cfg, "\n".join(lines))
        return post_id

    except Exception as exc:
        error = safe_error(exc)
        save_status("FAILED", topic=topic, error=error)
        telegram_send(
            cfg,
            "\n".join(
                [
                    "❌ LinkedIn Auto-Poster Failed",
                    "",
                    f"Stage/topic: {topic or 'startup'}",
                    "",
                    f"Error: {error}",
                    "",
                    f"Time: {datetime.now(timezone.utc).isoformat()}",
                ]
            ),
        )
        raise


def report_status(cfg: dict[str, str]) -> None:
    s = read_status()
    message = "\n".join(
        [
            "🤖 AI LinkedIn Poster",
            "",
            "Status: Ready",
            f"Last run: {s.get('timestamp', 'Unknown')}",
            f"Last result: {s.get('result', 'UNKNOWN')}",
            f"Topic: {s.get('topic') or 'N/A'}",
            f"Post ID: {s.get('post_id') or 'N/A'}",
        ]
    )
    telegram_send(cfg, message)
    print(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--postnow", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    try:
        cfg = load_config()
        if args.status:
            report_status(cfg)
            return 0

        publish_post(cfg)
        return 0
    except Exception as exc:
        log.error("Execution failed: %s", safe_error(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
