import re
import dateparser
from datetime import timedelta
import json
import google.generativeai as genai

# Assuming these service imports are correct and available
from gmail_service import send_email
from slack_service import post_message
from telegram_service import send_message
from calendar_service import create_event
from PipedreamConnector import proxy_request


def parse_priority(text: str) -> bool:
    """
    Checks for priority keywords in the text.
    """
    lowered = text.lower()
    return any(
        word in lowered for word in {"urgent", "asap", "immediately", "priority"}
    )


async def extract_and_decide_with_gemini(text: str):
    """
    Uses the Gemini API to extract structured event data and determine the intended service.
    """
    model = genai.GenerativeModel("gemini-1.5-pro-latest")

    # Define the functions/tools Gemini can "call"
    tools = [
        {
            "function_declarations": [
                {
                    "name": "send_email",
                    "description": "Send an email to one or more recipients.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of recipient email addresses.",
                            },
                            "subject": {
                                "type": "string",
                                "description": "Subject of the email.",
                            },
                            "body": {
                                "type": "string",
                                "description": "Full content of the email.",
                            },
                            "priority": {
                                "type": "boolean",
                                "description": "True if the email is urgent/high priority, false otherwise.",
                            },
                        },
                        "required": ["to", "subject", "body"],
                    },
                },
                {
                    "name": "post_message",
                    "description": "Post a message to a Slack channel.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "channel": {
                                "type": "string",
                                "description": "Slack channel name (e.g., '#general', '@username').",
                            },
                            "text": {
                                "type": "string",
                                "description": "Message content for Slack.",
                            },
                            "priority": {
                                "type": "boolean",
                                "description": "True if the message is urgent/high priority, false otherwise.",
                            },
                        },
                        "required": ["channel", "text"],
                    },
                },
                {
                    "name": "send_telegram_message",
                    "description": "Send a message to a Telegram chat.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "chat_id": {
                                "type": "string",
                                "description": "Telegram chat ID or username (e.g., '@mychannel', '12345').",
                            },
                            "text": {
                                "type": "string",
                                "description": "Message content for Telegram.",
                            },
                            "priority": {
                                "type": "boolean",
                                "description": "True if the message is urgent/high priority, false otherwise.",
                            },
                        },
                        "required": ["chat_id", "text"],
                    },
                },
                {
                    "name": "create_calendar_event",
                    "description": "Create a new event in the calendar.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "Summary/title of the calendar event. This should be a concise title, NOT include date/time/attendee details already captured in other fields.",
                            },
                            "start_time": {
                                "type": "string",
                                "format": "date-time",
                                "description": "REQUIRED. The precise start date AND time of the event in ISO 8601 format (e.g., 'YYYY-MM-DDTHH:MM:SS'). Extract this value precisely from the text. If only a date is given (e.g., 'tomorrow'), infer a reasonable default time (like 09:00:00 or 10:00:00). If only a time is given (e.g., '3 PM'), use the current date.",
                            },
                            "end_time": {
                                "type": "string",
                                "format": "date-time",
                                "description": "REQUIRED. The precise end date AND time of the event in ISO 8601 format. Calculate this value based on 'start_time' and any specified duration (e.g., '90 minutes', 'an hour and a half'). If no explicit end time or duration is provided, assume the event lasts for 1 hour from 'start_time'.",
                            },
                            "attendees": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of attendee email addresses.",
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description for the calendar event. (Optional)",
                            },
                        },
                        "required": ["summary", "start_time", "end_time"],
                    },
                },
                {
                    "name": "proxy_request",
                    "description": "Proxy a request to a Pipedream workflow. Use this for custom integrations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app": {
                                "type": "string",
                                "description": "Name of the application/service on Pipedream (e.g., 'your_crm').",
                            },
                            "path": {
                                "type": "string",
                                "description": "Specific endpoint path for the request (e.g., '/create_lead').",
                            },
                            "method": {
                                "type": "string",
                                "enum": ["GET", "POST", "PUT", "DELETE"],
                                "description": "HTTP method for the request.",
                            },
                            "data": {
                                "type": "object",
                                "description": "JSON payload for the request.",
                            },
                        },
                        "required": ["app", "path", "method", "data"],
                    },
                },
            ]
        }
    ]

    current_datetime_str = "Friday, July 25, 2025 at 10:49:02 PM IST"  # Hardcoded for consistent testing as per context
    current_datetime_obj = dateparser.parse(
        current_datetime_str,
        settings={"TIMEZONE": "Asia/Kolkata", "TO_TIMEZONE": "Asia/Kolkata"},
    )
    current_datetime_iso = (
        current_datetime_obj.isoformat(timespec="seconds")
        if current_datetime_obj
        else dateparser.parse("now").isoformat(timespec="seconds")
    )  # Fallback if parsing hardcoded fails

    prompt_parts = [
        f"You are an intelligent assistant that can route user requests to the appropriate service and extract all necessary details.",
        f"The current date and time is {current_datetime_iso}. Use this context strictly for relative dates like 'tomorrow', 'next week', 'tonight', and times like 'in 3 hours' or '10 AM'.",
        f"Analyze the following text and determine which single tool to use. Extract ALL relevant parameters for that tool, ensuring precise date and time extraction for calendar events.",
        f"For the 'create_calendar_event' tool:",
        f"- The 'summary' should be a concise title of the event, NOT including date/time/attendee details. Extract those into their specific 'start_time', 'end_time', and 'attendees' fields.",
        f"- 'start_time' and 'end_time' are CRITICAL. You MUST extract or calculate these into ISO 8601 format (YYYY-MM-DDTHH:MM:SS).",
        f"- If a duration is specified (e.g., '90 minutes', 'an hour and a half'), calculate 'end_time' based on 'start_time' and the duration.",
        f"- If only 'start_time' is given without explicit 'end_time' or 'duration', default the event to 1 hour long.",
        f"- If only a date is mentioned (e.g., 'tomorrow'), default the time to 09:00:00 on that date.",
        f"- If only a time is mentioned (e.g., '3 PM'), use the current date ({current_datetime_obj.strftime('%Y-%m-%d')}) for the event.",
        f"If the user's intent is unclear or no suitable tool is found, or if essential parameters are missing for the chosen tool (especially for calendar events), you MUST clearly state what information is missing.",
        f'Text to analyze: "{text}"',
    ]

    try:
        response = await model.generate_content_async(prompt_parts, tools=tools)

        if response.candidates and response.candidates[0].function_calls:
            function_call = response.candidates[0].function_calls[0]
            action = function_call.name
            params = {k: v for k, v in function_call.args.items()}

            # Post-processing for calendar event parameters
            if action == "create_calendar_event":
                start_dt = None
                end_dt = None

                # Parse start_time from Gemini's output
                if "start_time" in params and params["start_time"]:
                    # Pass current_datetime_obj as 'now' for context to dateparser
                    start_dt = dateparser.parse(
                        params["start_time"],
                        settings={
                            "TIMEZONE": "Asia/Kolkata",
                            "TO_TIMEZONE": "Asia/Kolkata",
                            "RELATIVE_BASE": current_datetime_obj,
                        },
                    )
                    if start_dt:
                        params["start_dt"] = start_dt
                    else:
                        print(
                            f"Warning: Could not parse start_time from Gemini: {params['start_time']}"
                        )
                    del params["start_time"]  # Remove original string key

                # Parse end_time from Gemini's output
                if "end_time" in params and params["end_time"]:
                    end_dt = dateparser.parse(
                        params["end_time"],
                        settings={
                            "TIMEZONE": "Asia/Kolkata",
                            "TO_TIMEZONE": "Asia/Kolkata",
                            "RELATIVE_BASE": current_datetime_obj,
                        },
                    )
                    if end_dt:
                        params["end_dt"] = end_dt
                    else:
                        print(
                            f"Warning: Could not parse end_time from Gemini: {params['end_time']}"
                        )
                    del params["end_time"]  # Remove original string key
                elif start_dt:
                    # Fallback: If Gemini didn't provide end_time but start_dt exists, default to 1 hour
                    print(
                        "Warning: Gemini did not provide end_time. Defaulting to 1 hour duration based on start_dt."
                    )
                    params["end_dt"] = start_dt + timedelta(hours=1)

                # If for some reason start_dt is still missing after parsing, it's an error
                if not start_dt:
                    return {
                        "action": "error",
                        "params": {
                            "message": "Calendar event requires a valid start time. Please specify a date and time.",
                            "body": text,
                        },
                    }

                # If end_dt is still missing after all attempts, ensure it's set for the service call
                if not params.get("end_dt") and start_dt:
                    params["end_dt"] = start_dt + timedelta(hours=1)
                    print(
                        "Debug: end_dt was still missing, setting to 1 hour after start_dt."
                    )

                # Ensure 'subject' is mapped from 'summary' for the create_event function
                params["subject"] = params.get("summary", "Calendar Event")
                if "summary" in params:
                    del params["summary"]

            # Add original text as 'body' if relevant for messaging services
            if action in ["send_email", "post_message", "send_telegram_message"]:
                if "text" in params:  # Ensure 'text' param is used for message content
                    params["body"] = params["text"]
                    del params["text"]
                else:
                    params["body"] = (
                        text  # Fallback to original text if no 'text' param from Gemini
                    )

            # Ensure 'priority' is set based on simple text parsing for all actions
            params["priority"] = parse_priority(text)

            # Map recipients/attendees for consistency in dispatch_actions
            if action == "send_email":
                params["recipients"] = params.get("to", [])
                if "to" in params:
                    del params["to"]
            elif action == "create_calendar_event":
                params["recipients"] = params.get("attendees", [])

            return {"action": action, "params": params}
        else:
            print(
                f"Gemini did not identify a clear action or returned text: {response.text}"
            )
            return {
                "action": "no_action",
                "params": {
                    "message": response.text or "Could not determine action.",
                    "body": text,
                },
            }

    except Exception as e:
        print(f"Error calling Gemini API or parsing response: {e}")
        return {
            "action": "error",
            "params": {"message": f"Error processing request: {e}", "body": text},
        }


# The dispatch_actions function is correct for its role and doesn't need changes for these issues.
# It correctly prepares parameters and calls the service.
async def dispatch_actions(action: str, params: dict, preview=False):
    """
    Dispatches the action to the correct service with extracted parameters.
    """
    service_map = {
        "send_email": send_email,
        "post_message": post_message,
        "send_telegram_message": send_message,
        "create_calendar_event": create_event,
        "proxy_request": proxy_request,
    }

    service_params = {}
    if action == "send_email":
        service_params = {
            "to": params.get("recipients", []),
            "subject": params.get("subject", "No subject found"),
            "body": params.get("body", ""),
            "priority": params.get("priority", False),
        }
        if not service_params["to"] and not preview:
            return {"error": "No recipient found for email."}
        if preview:
            return {
                "to": service_params["to"][0]
                if service_params["to"]
                else "example@example.com",
                "subject": service_params["subject"],
                "body": service_params["body"][:200] + "..."
                if len(service_params["body"]) > 200
                else service_params["body"],
                "priority": service_params["priority"],
            }
    elif action == "post_message":
        service_params = {
            "channel": params.get("channel", "#general"),
            "text": params.get("body", ""),
            "priority": params.get("priority", False),
        }
        if preview:
            return {
                "channel": service_params["channel"],
                "text": service_params["text"][:200] + "..."
                if len(service_params["text"]) > 200
                else service_params["text"],
            }
    elif action == "send_telegram_message":
        service_params = {
            "chat_id": params.get("chat_id", "@yourchannel"),
            "text": params.get("body", ""),
            "priority": params.get("priority", False),
        }
        if preview:
            return {
                "chat_id": service_params["chat_id"],
                "text": service_params["text"][:200] + "..."
                if len(service_params["text"]) > 200
                else service_params["text"],
            }
    elif action == "create_calendar_event":
        service_params = {
            "summary": params.get("subject", "No summary found"),
            "start_dt": params.get("start_dt"),
            "end_dt": params.get("end_dt"),
            "attendees": params.get("recipients", []),
            "description": params.get("description", params.get("body", "")),
        }
        if not service_params[
            "start_dt"
        ]:  # This should ideally be caught earlier by Gemini's output
            return {"error": "No valid start date found for calendar event."}
        if preview:
            return {
                "summary": service_params["summary"],
                "start": service_params["start_dt"].isoformat()
                if service_params["start_dt"]
                else "N/A",
                "end": service_params["end_dt"].isoformat()
                if service_params["end_dt"]
                else "N/A",
                "attendees": service_params["attendees"],
                "description": service_params["description"][:200] + "..."
                if len(service_params["description"]) > 200
                else service_params["description"],
            }
    elif action == "proxy_request":
        service_params = params
        if preview:
            return {"info": "Pipedream action preview", "details": params}
    else:
        return {"error": f"Unsupported action determined by AI: {action}"}

    if preview:
        return service_params

    if action in service_map:
        try:
            result = await service_map[action](**service_params)
            return result
        except Exception as e:
            return {"error": f"Failed to execute {action} service: {e}"}
    else:
        return {"error": f"Unknown action: {action}"}
