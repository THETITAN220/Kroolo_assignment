import os
from slack_sdk.web.async_client import AsyncWebClient

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
client = AsyncWebClient(token=SLACK_BOT_TOKEN)

DEFAULT_SLACK_CHANNEL = os.getenv("DEFAULT_SLACK_CHANNEL", "#general")


async def post_message(channel: str = "", text: str = "", priority=False, **kwargs):
    """
    Posts a message to a Slack channel.
    If channel is None, defaults to DEFAULT_SLACK_CHANNEL.
    """
    if channel is None:
        channel = DEFAULT_SLACK_CHANNEL

    try:
        resp = await client.chat_postMessage(channel=channel, text=text)
        return {"status": "sent", "ts": resp["ts"], "channel": channel}
    except Exception as e:
        return {"error": str(e), "channel": channel}
