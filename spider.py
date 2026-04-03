import aiohttp
from typing import Optional
import logging
import asyncio
import random

logger = logging.getLogger(__name__)


class WikiSpider:
    EN_URL = "https://scavprototype.wiki.gg/api.php"
    ZH_URL = "https://scavprototype.wiki.gg/zh/api.php"

    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _create_session(self) -> aiohttp.ClientSession:
        if self._session and not self._session.closed:
            return self._session

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "DNT": "1",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }

        connector = aiohttp.TCPConnector(
            ssl=True,
            enable_cleanup_closed=True,
            force_close=False,
            limit=10,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )

        self._session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers=headers,
            connector=connector,
            cookie_jar=aiohttp.CookieJar(),
            auto_decompress=True,
        )

        return self._session

    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

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

        await asyncio.sleep(0.5)
        result = await self._search_single(self.EN_URL, params)
        if result:
            return result

        return []

    async def _search_single(self, url: str, params: dict) -> Optional[list]:
        session = await self._create_session()

        try:
            async with session.get(url, params=params, allow_redirects=True) as resp:
                logger.debug(f"搜索响应状态码：{resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    if len(data) >= 2 and data[1]:
                        return data[1]
                elif resp.status == 403:
                    logger.error(f"搜索 API 返回 403，可能被 Cloudflare 限制")
                elif resp.status == 429:
                    logger.warning(f"搜索 API 返回 429，请求过于频繁")
                else:
                    logger.warning(f"搜索失败，状态码：{resp.status}")
        except asyncio.TimeoutError:
            logger.warning(f"搜索超时 {url}")
        except aiohttp.ClientError as e:
            logger.warning(f"搜索失败 {url}: {type(e).__name__}: {e}")
        except Exception as e:
            logger.error(f"搜索异常 {url}: {type(e).__name__}: {e}")

        return None

    async def _request(self, params: dict) -> dict:
        result = await self._request_single(self.ZH_URL, params)
        if result:
            return result

        await asyncio.sleep(0.5)
        result = await self._request_single(self.EN_URL, params)
        if result:
            return result

        return {"error": "Both API endpoints failed"}

    async def _request_single(self, url: str, params: dict) -> Optional[dict]:
        session = await self._create_session()

        try:
            async with session.get(url, params=params, allow_redirects=True) as resp:
                logger.debug(f"请求响应状态码：{resp.status}")
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 403:
                    logger.error(f"API 返回 403，可能被 Cloudflare 限制访问")
                    return None
                elif resp.status == 429:
                    logger.warning(f"API 返回 429，请求过于频繁")
                    await asyncio.sleep(2)
                    return None
                else:
                    logger.warning(f"API 返回状态码 {resp.status}")
                    return None
        except asyncio.TimeoutError:
            logger.warning(f"请求超时 {url}")
            return None
        except aiohttp.ClientError as e:
            logger.warning(f"请求失败 {url}: {type(e).__name__}: {e}")
            return None
        except Exception as e:
            logger.error(f"请求异常 {url}: {type(e).__name__}: {e}")
            return None

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

