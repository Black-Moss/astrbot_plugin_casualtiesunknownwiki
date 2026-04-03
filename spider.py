import aiohttp
from typing import Optional
import logging
from astrbot.api import logger
from curl_cffi import requests as curl_requests

class WikiSpider:
    EN_URL = "https://scavprototype.wiki.gg/api.php"
    ZH_URL = "https://scavprototype.wiki.gg/zh/api.php"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = curl_requests.Session(
            impersonate="chrome124",
            timeout=timeout,
            verify=False
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
        logger.info(f"[WikiSpider] 查询：{params}")
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
            response = self._make_request(self.ZH_URL, params)
            if response.status_code == 200:
                data = response.json()
                if len(data) >= 2 and data[1]:
                    return data[1]
        except Exception as e:
            logger.warning(f"中文 API 搜索失败：{e}")

        # 中文失败后尝试英文 API
        try:
            response = self._make_request(self.EN_URL, params)
            if response.status_code == 200:
                data = response.json()
                if len(data) >= 2 and data[1]:
                    return data[1]
        except Exception as e:
            logger.warning(f"英文 API 搜索失败：{e}")

        return []

    def _make_request(self, url: str, params: dict = None):
        """封装请求头设置"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        }
        
        return self.session.get(url, params=params, headers=headers)

    async def _request(self, params: dict) -> dict:
        # 优先尝试中文 API
        try:
            logger.info(f"[WikiSpider] 中文查询：{params}")
            response = self._make_request(self.ZH_URL, params)
            logger.info(f"[WikiSpider] 中文响应状态码：{response.status_code}")
            if response.status_code != 200:
                logger.error(f"[WikiSpider] 中文响应内容前 200 字节：{response.text[:200]}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"[WikiSpider] 中文 API 返回非 200 状态码：{response.status_code}")
        except Exception as e:
            logger.error(f"[WikiSpider] 中文 API 请求异常：{type(e).__name__}: {e}")

        # 中文失败后尝试英文 API
        try:
            logger.info(f"[WikiSpider] 英文查询：{params}")
            response = self._make_request(self.EN_URL, params)
            logger.info(f"[WikiSpider] 英文响应状态码：{response.status_code}")
            if response.status_code != 200:
                logger.error(f"[WikiSpider] 英文响应内容前 200 字节：{response.text[:200]}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"[WikiSpider] 英文 API 返回非 200 状态码：{response.status_code}")
        except Exception as e:
            logger.error(f"[WikiSpider] 英文 API 请求异常：{type(e).__name__}: {e}")

        return {"error": "两个 API 都失效了"}

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
