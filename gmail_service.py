import os
import httpx
from dotenv import load_dotenv

load_dotenv()

PIPEDREAM_API_KEY = os.getenv("PIPEDREAM_API_KEY")
PIPEDREAM_GMAIL_ENDPOINT = "https://eoti9elkn97xcob.m.pipedream.net"


async def send_email(to, subject, body, priority=False, **kwargs):
    headers = {"Authorization": f"Bearer {PIPEDREAM_API_KEY}"}
    if isinstance(to, list):
        to = ", ".join(to)
    payload = {"to": to, "subject": subject, "body": body, "priority": priority}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            PIPEDREAM_GMAIL_ENDPOINT, json=payload, headers=headers
        )
        try:
            resp_json = resp.json()
        except Exception:
            resp_json = None  # Could not parse JSON
        if resp.status_code in (200, 202):
            return {"status": "email sent", "detail": resp_json or resp.text}
        else:
            # Return more info on failure
            return {
                "error": f"Failed to send email, Status code: {resp.status_code}",
                "detail": resp_json or resp.text,
            }
