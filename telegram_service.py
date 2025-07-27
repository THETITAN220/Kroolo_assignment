import os
import httpx

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


async def send_telegram_message(chat_id: str, text: str, priority=False, **kwargs):
    payload = {"chat_id": chat_id, "text": text}
    async with httpx.AsyncClient() as client:
        resp = await client.post(TELEGRAM_API_URL, json=payload)
        if resp.status_code == 200:
            return {"status": "sent", "chat_id": chat_id}
        else:
            return {"error": "Failed to send Telegram message", "detail": resp.text}
