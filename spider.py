import aiohttp
from typing import Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


class WikiSpider:
    EN_URL = "https://scavprototype.wiki.gg/api.php"
    ZH_URL = "https://scavprototype.wiki.gg/zh/api.php"

    def __init__(self, timeout: int = 15):
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def _create_session(self) -> aiohttp.ClientSession:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

        connector = aiohttp.TCPConnector(
            ssl=True,
            enable_cleanup_closed=True,
            force_close=False,
        )

        return aiohttp.ClientSession(
            timeout=self.timeout,
            headers=headers,
            connector=connector,
            cookie_jar=aiohttp.CookieJar()
        )

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

        result = await self._search_single(self.ZH_URL, params)
        if result:
            return result

        result = await self._search_single(self.EN_URL, params)
        if result:
            return result

        return []

    async def _search_single(self, url: str, params: dict) -> Optional[list]:
        session = None
        try:
            session = await self._create_session()

            async with session.get(url, params=params, allow_redirects=True) as resp:
                logger.debug(f"搜索响应状态码：{resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    if len(data) >= 2 and data[1]:
                        return data[1]
                else:
                    logger.warning(f"搜索失败，状态码：{resp.status}")
        except Exception as e:
            logger.warning(f"搜索失败 {url}: {type(e).__name__}: {e}")
        finally:
            if session:
                await session.close()
        return None

    async def _request(self, params: dict) -> dict:
        result = await self._request_single(self.ZH_URL, params)
        if result:
            return result

        result = await self._request_single(self.EN_URL, params)
        if result:
            return result

        return {"error": "Both API endpoints failed"}

    async def _request_single(self, url: str, params: dict) -> Optional[dict]:
        session = None
        try:
            session = await self._create_session()

            async with session.get(url, params=params, allow_redirects=True) as resp:
                logger.debug(f"请求响应状态码：{resp.status}")
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 403:
                    logger.error(f"API 返回 403，可能被 Cloudflare 限制访问")
                    return None
                else:
                    logger.warning(f"API 返回状态码 {resp.status}")
                    return None
        except Exception as e:
            logger.warning(f"请求失败 {url}: {type(e).__name__}: {e}")
            return None
        finally:
            if session:
                await session.close()

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

