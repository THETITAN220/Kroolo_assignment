import os
import dateparser
from datetime import timedelta
from google import genai
from google.genai import types
from dotenv import load_dotenv

from gmail_service import send_email
from slack_service import post_message
from telegram_service import send_telegram_message
from calendar_service import create_event

load_dotenv()


def parse_priority(text: str) -> bool:
    lowered = text.lower()
    return any(
        word in lowered for word in {"urgent", "asap", "immediately", "priority"}
    )


client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


async def extract_and_decide_with_gemini(text: str):
    tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="send_email",
                    description="Send an email.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "to": types.Schema(
                                type=types.Type.ARRAY,
                                items=types.Schema(type=types.Type.STRING),
                            ),
                            "subject": types.Schema(type=types.Type.STRING),
                            "body": types.Schema(type=types.Type.STRING),
                            "priority": types.Schema(type=types.Type.BOOLEAN),
                        },
                        required=["to", "subject", "body"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="post_message",
                    description="Post to Slack.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "channel": types.Schema(type=types.Type.STRING),
                            "text": types.Schema(type=types.Type.STRING),
                            "priority": types.Schema(type=types.Type.BOOLEAN),
                        },
                        required=["channel", "text"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="send_telegram_message",
                    description="Send Telegram message.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "chat_id": types.Schema(type=types.Type.STRING),
                            "text": types.Schema(type=types.Type.STRING),
                            "priority": types.Schema(type=types.Type.BOOLEAN),
                        },
                        required=["chat_id", "text"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="create_calendar_event",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "summary": types.Schema(type=types.Type.STRING),
                            "start_time": types.Schema(
                                type=types.Type.STRING, format="date-time"
                            ),
                            "end_time": types.Schema(
                                type=types.Type.STRING, format="date-time"
                            ),
                            "attendees": types.Schema(
                                type=types.Type.ARRAY,
                                items=types.Schema(type=types.Type.STRING),
                            ),
                            "description": types.Schema(type=types.Type.STRING),
                        },
                        required=["summary", "start_time", "end_time"],
                    ),
                ),
            ]
        )
    ]
    current_datetime_str = "Friday, July 25, 2025 at 10:49:02 PM IST"
    current_datetime_obj = dateparser.parse(
        current_datetime_str,
        settings={"TIMEZONE": "Asia/Kolkata", "TO_TIMEZONE": "Asia/Kolkata"},
    )
    current_datetime_iso = (
        current_datetime_obj.isoformat(timespec="seconds")
        if current_datetime_obj
        else dateparser.parse("now").isoformat(timespec="seconds")
    )

    prompt = [
        f"You are an intelligent assistant that can route user requests. The current date and time is {current_datetime_iso}.",
        f'Below is the user\'s request: "{text}"',
        (
            "For calendar events: Extract summary (title), and ensure start_time and end_time are ISO 8601 (YYYY-MM-DDTHH:MM:SS). "
            "If date or time missing, set defaults as per business rules. Report missing info clearly if not extractable."
        ),
    ]
    try:
        response = await client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(tools=tools),
        )
        candidate = response.candidates[0]
        part = (
            candidate.content.parts[0]
            if candidate.content and candidate.content.parts
            else None
        )
        function_call = getattr(part, "function_call", None)
        if function_call:
            action = function_call.name
            params = dict(function_call.args)
            # Calendar event datetimes
            if action == "create_calendar_event":
                base_settings = {
                    "TIMEZONE": "Asia/Kolkata",
                    "TO_TIMEZONE": "Asia/Kolkata",
                }
                if current_datetime_obj:
                    base_settings["RELATIVE_BASE"] = current_datetime_obj
                start_dt = (
                    dateparser.parse(
                        params.get("start_time", ""), settings=base_settings
                    )
                    if params.get("start_time")
                    else None
                )
                end_dt = (
                    dateparser.parse(params.get("end_time", ""), settings=base_settings)
                    if params.get("end_time")
                    else None
                )
                if not start_dt:
                    return {
                        "action": "error",
                        "params": {
                            "message": "Missing or unparseable start time for calendar event.",
                            "body": text,
                        },
                    }
                if not end_dt and start_dt:
                    end_dt = start_dt + timedelta(hours=1)
                params["start_dt"] = start_dt
                params["end_dt"] = end_dt
                params["subject"] = params.get("summary", "Calendar Event")
                params.pop("summary", None)

            if action == "send_email":
                params["recipients"] = params.get("to", [])
                params.pop("to", None)
            elif action == "create_calendar_event":
                params["recipients"] = params.get("attendees", [])
            if action in ["post_message", "send_telegram_message"]:
                if "text" in params:
                    params["body"] = params.pop("text")
                else:
                    params["body"] = text
            params["priority"] = parse_priority(text)
            return {"action": action, "params": params}
        return {
            "action": "no_action",
            "params": {"message": "No action detected", "body": text},
        }
    except Exception as e:
        return {
            "action": "error",
            "params": {"message": f"Error from Gemini SDK: {e}", "body": text},
        }


async def dispatch_actions(action: str, params: dict, preview: bool = False):
    if preview:
        return {"preview": f"Action: {action}, Parameters: {params}"}
    if action == "send_email":
        recipients = params.get("recipients")
        to = ", ".join(recipients) if isinstance(recipients, list) else recipients
        return await send_email(
            to=to,
            subject=params.get("subject", ""),
            body=params.get("body", ""),
            priority=params.get("priority", False),
        )
    elif action == "post_message":
        return await post_message(
            channel=params.get("channel"),
            text=params.get("body", ""),
            priority=params.get("priority", False),
        )
    elif action == "send_telegram_message":
        return await send_telegram_message(
            chat_id=params.get("chat_id"),
            text=params.get("body", ""),
            priority=params.get("priority", False),
        )
    elif action == "create_calendar_event":
        return await create_event(
            summary=params.get("subject", "Calendar Event"),
            start_dt=params.get("start_dt"),
            end_dt=params.get("end_dt"),
            attendees=params.get("recipients", []),
        )
    else:
        return {"error": f"Unknown action '{action}'"}
