import aiohttp
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class WikiSpider:
    EN_URL = "https://scavprototype.wiki.gg/api.php"
    ZH_URL = "https://scavprototype.wiki.gg/zh/api.php"

    def __init__(self, timeout: int = 10):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.headers = {
            "User-Agent": "AstrBot-CasualtiesUnknownWiki-Plugin/1.0.0"
        }

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
        # 优先尝试中文 API
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(self.ZH_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if len(data) >= 2 and data[1]:
                            return data[1]
        except Exception as e:
            logger.warning(f"中文 API 搜索失败：{e}")

        # 中文失败后尝试英文 API
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(self.EN_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if len(data) >= 2 and data[1]:
                            return data[1]
        except Exception as e:
            logger.warning(f"英文 API 搜索失败：{e}")

        return []

    async def _request(self, params: dict) -> dict:
        # 优先尝试中文 API
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(self.ZH_URL, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.warning(f"中文 API 请求失败：{e}")

        # 中文失败后尝试英文 API
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(self.EN_URL, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"英文 API 请求失败：{e}")

        return {"error": "Both API endpoints failed"}

    @staticmethod
    def parse_page_content(data: dict) -> Optional[dict]:
        if "error" in data:
            return None
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

