import aiohttp
from typing import Optional


class WikiSpider:
    EN_URL = "https://scavprototype.wiki.gg/api.php"
    ZH_URL = "https://scavprototype.wiki.gg/zh/api.php"

    def __init__(self, timeout: int = 10):
        self.timeout = aiohttp.ClientTimeout(total=timeout)


    async def query_page(self, title: str, redirects: bool = True) -> dict:
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "revisions",
            "rvprop": "content",
            "redirects": 1 if redirects else 0
        }
        return await self._request(params)

    async def search(self, keyword: str, limit: int = 10) -> list:
        params = {
            "action": "opensearch",
            "format": "json",
            "search": keyword,
            "limit": limit
        }
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.BASE_URL, params=params) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    if len(data) >= 2:
                        return data[1]
                    return []
        except Exception:
            return []

    async def _request(self, params: dict) -> dict:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.BASE_URL, params=params) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def parse_page_content(data: dict) -> Optional[dict]:
        query = data.get("query", {})
        pages = query.get("pages", {})
        for page_id, page_info in pages.items():
            if "revisions" in page_info:
                return {
                    "id": page_id,
                    "title": page_info.get("title"),
                    "content": page_info["revisions"][0]["*"]
                }
        return None
