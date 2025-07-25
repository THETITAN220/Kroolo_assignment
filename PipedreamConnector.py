import os
import httpx

PIPEDREAM_API_KEY = os.getenv("PIPEDREAM_API_KEY")


async def proxy_request(app: str, path: str, method="GET", data=None):
    """
    Proxy request to Pipedream Connect API.
    """
    base_url = f"https://api.pipedream.com/v1/apps/{app}/"
    url = base_url + path.lstrip("/")

    headers = {
        "Authorization": f"Bearer {PIPEDREAM_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        if method.upper() == "POST":
            response = await client.post(url, json=data, headers=headers)
        elif method.upper() == "PUT":
            response = await client.put(url, json=data, headers=headers)
        else:
            response = await client.get(url, params=data, headers=headers)

    if response.status_code in (200, 201, 202):
        return response.json()
    else:
        return {
            "error": f"Request failed with status {response.status_code}",
            "detail": response.text,
        }
