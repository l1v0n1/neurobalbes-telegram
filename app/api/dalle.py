from base64 import b64decode
import aiohttp
import asyncio


async def dalle_api(query):
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.post('https://bf.dallemini.ai/generate', json={"prompt": query}) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    break
                else:
                    print(f"Request returned status code {response.status}, trying again in 2 seconds")
                    await asyncio.sleep(2)
    return [b64decode(img) for img in response["images"]]
