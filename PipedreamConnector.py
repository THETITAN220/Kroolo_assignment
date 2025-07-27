import os
import httpx

PIPEDREAM_API_KEY = os.getenv("PIPEDREAM_API_KEY")


async def pipedream_proxy(endpoint: str, payload: dict):
    headers = {"Authorization": f"Bearer {PIPEDREAM_API_KEY}"}
    async with httpx.AsyncClient() as client:
        return await client.post(endpoint, json=payload, headers=headers)
