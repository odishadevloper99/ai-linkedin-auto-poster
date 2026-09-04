import base64
import hashlib
from urllib.parse import quote, urlencode
from .http import request


class Image:
    def __init__(self, c):
        self.c = c

    def _aicredits(self, prompt):
        body = {
            "model": self.c.aicredits_image_model,
            "prompt": str(prompt),
            "size": self.c.image_size,
            "quality": self.c.image_quality,
            "n": 1,
            "response_format": "b64_json",
        }
        r = request(
            "POST",
            self.c.aicredits_base_url.rstrip("/") + "/images/generations",
            headers={
                "Authorization": f"Bearer {self.c.aicredits_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=max(180, self.c.timeout),
            retries=self.c.retries,
        )
        if not r.ok:
            raise RuntimeError(f"AICredits image HTTP {r.status_code}: {r.text[:1000]}")
        try:
            item = r.json()["data"][0]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("AICredits image response missing data[0]") from exc

        content_type = "image/png"
        if item.get("b64_json"):
            try:
                content = base64.b64decode(item["b64_json"], validate=True)
            except Exception as exc:
                raise RuntimeError("AICredits returned invalid base64 image data") from exc
        elif item.get("url"):
            img = request(
                "GET",
                item["url"],
                headers={"Accept": "image/jpeg,image/png,image/webp,*/*"},
                timeout=max(120, self.c.timeout),
                retries=self.c.retries,
            )
            if not img.ok:
                raise RuntimeError(f"AICredits image download HTTP {img.status_code}")
            content = img.content
            content_type = img.headers.get("Content-Type", content_type).split(";", 1)[0].lower()
        else:
            raise RuntimeError("AICredits image response contained neither b64_json nor url")

        if len(content) < 100_000:
            raise RuntimeError("AICredits returned an unexpectedly small image")
        return content, hashlib.sha256(content).hexdigest(), content_type

    def _pollinations(self, prompt):
        params = {
            "width": max(1200, int(self.c.image_width)),
            "height": max(627, int(self.c.image_height)),
            "model": self.c.image_model,
            "nologo": "true",
            "enhance": "true",
            "private": "true",
            "negative_prompt": (
                "blurry, low resolution, soft focus, pixelated, jpeg artifacts, "
                "watermark, logo, text, distorted anatomy, duplicate objects, "
                "oversaturated, muddy details"
            ),
        }
        u = self.c.image_base + quote(str(prompt), safe="") + "?" + urlencode(params)
        r = request(
            "GET",
            u,
            headers={"Accept": "image/jpeg,image/png,image/webp,*/*"},
            timeout=max(120, self.c.timeout),
            retries=self.c.retries,
        )
        content_type = r.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if not r.ok or not content_type.startswith("image/"):
            raise RuntimeError(f"Image provider HTTP {r.status_code}")
        if len(r.content) < 100_000:
            raise RuntimeError("Image provider returned an unexpectedly small image")
        return r.content, hashlib.sha256(r.content).hexdigest(), content_type

    def generate(self, prompt):
        # AICredits is the primary provider when configured. Pollinations remains
        # as the legacy provider so existing deployments without the new key keep working.
        if self.c.aicredits_key:
            return self._aicredits(prompt)
        return self._pollinations(prompt)
