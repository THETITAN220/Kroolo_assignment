import os
import httpx
from dotenv import load_dotenv

load_dotenv()

PIPEDREAM_API_KEY = os.getenv("PIPEDREAM_API_KEY")
PIPEDREAM_CALENDAR_ENDPOINT = "https://eoh6ocgelltctgo.m.pipedream.net"


async def create_event(summary, start_dt, end_dt, attendees=None, **kwargs):
    if attendees is None:
        attendees = []
    headers = {"Authorization": f"Bearer {PIPEDREAM_API_KEY}"}
    payload = {
        "summary": summary or "No Title",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        "attendees": [{"email": e} for e in attendees if e],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            PIPEDREAM_CALENDAR_ENDPOINT, json=payload, headers=headers
        )
        try:
            resp_json = resp.json()
        except Exception:
            resp_json = None
        if resp.status_code in (200, 202):
            return {"status": "event created", "detail": resp_json or resp.text}
        else:
            return {
                "error": f"Failed to create event, status code: {resp.status_code}",
                "detail": resp_json or resp.text,
            }
