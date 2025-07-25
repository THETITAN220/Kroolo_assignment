import os
import httpx

PIPEDREAM_API_KEY = os.getenv("PIPEDREAM_API_KEY")
PIPEDREAM_CALENDAR_ENDPOINT = (
    "https://eoh6ocgelltctgo.m.pipedream.net"  # Replace with your Pipedream endpoint
)


async def create_event(summary: str, start_dt, end_dt, attendees: list, **kwargs):
    """
    Creates a Google Calendar event via Pipedream workflow.
    """
    headers = {"Authorization": f"Bearer {PIPEDREAM_API_KEY}"}
    payload = {
        "summary": summary,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "attendees": [{"email": e} for e in attendees if e],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            PIPEDREAM_CALENDAR_ENDPOINT, json=payload, headers=headers
        )
        if resp.status_code == 200 or resp.status_code == 202:
            return {"status": "event created", "detail": resp.json()}
        else:
            return {"error": "Failed to create event", "detail": resp.text}
