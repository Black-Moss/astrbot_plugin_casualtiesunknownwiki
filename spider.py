import aiohttp
from typing import Optional
import logging
import asyncio
import random

logger = logging.getLogger(__name__)


class WikiSpider:
    EN_URL = "https://scavprototype.wiki.gg/api.php"
    ZH_URL = "https://scavprototype.wiki.gg/zh/api.php"

    def __init__(self, timeout: int = 10):
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

        self.headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
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
                    logger.debug(f"中文搜索响应状态码：{resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        if len(data) >= 2 and data[1]:
                            return data[1]
        except Exception as e:
            logger.warning(f"中文 API 搜索失败：{type(e).__name__}: {e}")

        # 中文失败后尝试英文 API
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(self.EN_URL, params=params) as resp:
                    logger.debug(f"英文搜索响应状态码：{resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        if len(data) >= 2 and data[1]:
                            return data[1]
        except Exception as e:
            logger.warning(f"英文 API 搜索失败：{type(e).__name__}: {e}")

        return []

    async def _request(self, params: dict) -> dict:
        errors = []

        connector = aiohttp.TCPConnector(ssl=False)

        # 优先尝试中文 API
        try:
            logger.debug(f"请求中文 API: {self.ZH_URL}, params={params}")
            async with aiohttp.ClientSession(
                    timeout=self.timeout,
                    headers=self.headers,
                    connector=connector
            ) as session:
                async with session.get(self.ZH_URL, params=params, auto_decompress=False) as resp:
                    logger.debug(f"中文 API 响应状态码：{resp.status}, 响应头：{dict(resp.headers)}")
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 403:
                        error_msg = f"中文 API 拒绝访问 (403)"
                        logger.error(error_msg)
                        errors.append(error_msg)
                    else:
                        errors.append(f"中文 API 返回状态码 {resp.status}")
        except Exception as e:
            error_msg = f"中文 API 请求失败：{type(e).__name__}: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)

        # 中文失败后尝试英文 API
        try:
            logger.debug(f"请求英文 API: {self.EN_URL}, params={params}")
            async with aiohttp.ClientSession(
                    timeout=self.timeout,
                    headers=self.headers,
                    connector=connector
            ) as session:
                async with session.get(self.EN_URL, params=params, auto_decompress=False) as resp:
                    logger.debug(f"英文 API 响应状态码：{resp.status}, 响应头：{dict(resp.headers)}")
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 403:
                        error_msg = f"英文 API 拒绝访问 (403)"
                        logger.error(error_msg)
                        errors.append(error_msg)
                    else:
                        errors.append(f"英文 API 返回状态码 {resp.status}")
        except Exception as e:
            error_msg = f"英文 API 请求失败：{type(e).__name__}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        logger.error(f"两个 API 端点都失败了：{errors}")
        return {"error": f"Both API endpoints failed: {'; '.join(errors)}"}

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

