import os
import base64
from email.mime.text import MIMEText
import httpx

PIPEDREAM_API_KEY = os.getenv("PIPEDREAM_API_KEY")
PIPEDREAM_GMAIL_ENDPOINT = "https://eoti9elkn97xcob.m.pipedream.net"


async def send_email(to: str, subject: str, body: str, priority=False, **kwargs):
    """
    Sends email through Pipedream workflow or directly using Gmail API.
    Here we POST data to Pipedream API that triggers email send.
    """
    headers = {"Authorization": f"Bearer {PIPEDREAM_API_KEY}"}

    # Construct payload
    payload = {"to": to, "subject": subject, "body": body, "priority": priority}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            PIPEDREAM_GMAIL_ENDPOINT, json=payload, headers=headers
        )
        if resp.status_code == 200 or resp.status_code == 202:
            return {"status": "email sent", "detail": resp.json()}
        else:
            return {"error": "Failed to send email", "detail": resp.text}
