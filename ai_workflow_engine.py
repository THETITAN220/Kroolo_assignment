import re
import dateparser
from datetime import timedelta

from gmail_service import send_email
from slack_service import post_message
from telegram_service import send_message
from calendar_service import create_event
from PipedreamConnector import proxy_request

PRIORITY_KEYWORDS = {"urgent", "asap", "immediately", "priority"}


def parse_priority(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in PRIORITY_KEYWORDS)


def extract_basic_entities(text: str):
    # Extract dates eg: "tomorrow at 5 pm"
    dt = dateparser.parse(text)

    # Extract emails with simple regex
    emails = re.findall(r"[\w\.-]+@[\w\.-]+", text)

    # Extract quoted text as possible subject/body
    quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", text)
    subject = (
        quoted[0][0]
        if quoted and quoted[0][0]
        else (quoted[0][1] if quoted and quoted[0][1] else None)
    )
    if not subject:
        subject = text[:50]

    return {
        "datetime": dt,
        "recipients": emails,
        "subject": subject,
        "priority": parse_priority(text),
        "body": text,
    }


def detect_actions(text: str, forced_channels=None):
    text_lower = text.lower()
    actions = []

    # If caller pre-selects channels
    if forced_channels:
        # Only add actions for these
        for chan in forced_channels:
            if chan in {"email", "slack", "telegram", "calendar", "pipedream"}:
                actions.append(chan)
        return actions

    # Otherwise detect based on keywords
    if "email" in text_lower or "mail" in text_lower:
        actions.append("email")
    if "slack" in text_lower:
        actions.append("slack")
    if "telegram" in text_lower:
        actions.append("telegram")
    if "calendar" in text_lower or "event" in text_lower or "schedule" in text_lower:
        actions.append("calendar")
    if "connect:" in text_lower:
        actions.append("pipedream")

    return actions


async def dispatch_actions(channel, message, preview=False, extra_params=None):
    extra_params = extra_params or {}
    entities = extract_basic_entities(message)

    if channel == "email":
        if preview:
            return {
                "to": entities["recipients"][0]
                if entities["recipients"]
                else "example@example.com",
                "subject": entities["subject"],
                "body": entities["body"],
                "priority": entities["priority"],
            }

        # Send actual email
        to = entities["recipients"][0] if entities["recipients"] else None
        if not to:
            return {"error": "No recipient found for email."}
        result = await send_email(
            to=to,
            subject=entities["subject"],
            body=entities["body"],
            priority=entities["priority"],
        )
        return result

    elif channel == "slack":
        # Fix: Ensure channel is always a string, fallback to "#general"
        slack_channel = extra_params.get("slack_channel") or "#general"
        if preview:
            return {
                "channel": slack_channel,
                "text": entities["body"][:200],
            }
        result = await post_message(
            channel=slack_channel,
            text=entities["body"],
            priority=entities["priority"],
        )
        return result

    elif channel == "telegram":
        if preview:
            return {"chat_id": "@yourchannel", "text": entities["body"][:200]}

        result = await send_message(
            chat_id="@yourchannel", text=entities["body"], priority=entities["priority"]
        )
        return result

    elif channel == "calendar":
        if preview:
            return {
                "summary": entities["subject"],
                "start": entities["datetime"].isoformat()
                if entities["datetime"]
                else "N/A",
                "end": (entities["datetime"] + timedelta(hours=1)).isoformat()
                if entities["datetime"]
                else "N/A",
                "attendees": entities["recipients"],
            }
        if not entities["datetime"]:
            return {"error": "No valid datetime found for calendar event."}
        result = await create_event(
            summary=entities["subject"],
            start_dt=entities["datetime"],
            end_dt=entities["datetime"] + timedelta(hours=1),
            attendees=entities["recipients"],
        )
        return result

    elif channel == "pipedream":
        if preview:
            return {"info": "Pipedream action preview"}

        # For demonstration, proxy fixed path (adjust for your flows)
        result = await proxy_request(
            app="your_app",
            path="your_endpoint",
            method="POST",
            data={"message": message},
        )
        return result

    else:
        return {"error": f"Unsupported channel: {channel}"}
