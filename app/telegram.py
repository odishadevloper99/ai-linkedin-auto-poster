import requests


class Telegram:
    def __init__(self, c):
        self.c = c

    def _url(self, method):
        return f"https://api.telegram.org/bot{self.c.telegram_token}/{method}"

    def send(self, text, buttons=None):
        if not self.c.telegram_token or not self.c.telegram_chat_id:
            return False
        d = {"chat_id": self.c.telegram_chat_id, "text": str(text)[:4096], "disable_web_page_preview": False}
        if buttons:
            d["reply_markup"] = {"inline_keyboard": buttons}
        r = requests.post(self._url("sendMessage"), json=d, timeout=30)
        r.raise_for_status()
        return True

    def photo(self, b, caption=""):
        if not self.c.telegram_token or not self.c.telegram_chat_id:
            return False
        r = requests.post(
            self._url("sendPhoto"),
            data={"chat_id": self.c.telegram_chat_id, "caption": str(caption)[:1024]},
            files={"photo": ("linkedin.jpg", b, "image/jpeg")},
            timeout=60,
        )
        r.raise_for_status()
        return True

    def answer(self, callback_id):
        if not self.c.telegram_token:
            return
        requests.post(
            self._url("answerCallbackQuery"),
            json={"callback_query_id": callback_id},
            timeout=20,
        )

    def admin(self, uid):
        return bool(self.c.telegram_admin_id) and str(uid) == str(self.c.telegram_admin_id)

    def set_webhook(self):
        if not self.c.telegram_token or not self.c.telegram_webhook_url:
            return {"ok": False, "reason": "missing Telegram token or webhook URL"}
        payload = {"url": self.c.telegram_webhook_url}
        if self.c.telegram_webhook_secret:
            payload["secret_token"] = self.c.telegram_webhook_secret
        r = requests.post(self._url("setWebhook"), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def delete_webhook(self):
        if not self.c.telegram_token:
            return False
        r = requests.post(self._url("deleteWebhook"), timeout=30)
        r.raise_for_status()
        return True
