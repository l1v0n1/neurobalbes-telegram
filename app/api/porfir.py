import aiohttp


async def porfirevich(query):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://pelevin.gpt.dobro.ai/generate/",
            json={"prompt": query, "num_samples": 1, 'lenght': 60},
        ) as resp:
            response = await resp.json()
            return "{}{}".format(query, response["replies"][0])
