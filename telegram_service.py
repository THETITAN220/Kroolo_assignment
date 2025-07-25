import os
from telegram import Bot

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def send_message(chat_id: str, text: str, priority=False, **kwargs):
    """
    Sends a telegram message via bot.
    """
    try:
        sent_message = await bot.send_message(chat_id=chat_id, text=text)
        return {"status": "sent", "message_id": sent_message.message_id}
    except Exception as e:
        return {"error": str(e)}
