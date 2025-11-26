import json
import asyncio
from bot import dp, bot
from aiogram.types import Update

async def process_update(update_data: dict):
    update = Update.model_validate(update_data)
    await dp.feed_update(bot, update)

def handler(request, response):
    if request.method == "POST":
        payload = request.json()
        asyncio.run(process_update(payload))
        return response.status(200).send("OK")
    return response.status(200).send("BOT IS RUNNING")

