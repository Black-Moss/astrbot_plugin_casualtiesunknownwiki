from curl_cffi import requests
from typing import Optional
from astrbot.api import logger
import time


class WikiSpider:
    BASE_URL = "https://scavprototype.wiki.gg/zh/api.php"

    # 使用真实的浏览器 User-Agent
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://scavprototype.wiki.gg/",
        "sec-ch-ua": '"Chromium";v="131", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

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
            resp = self._make_request(params)
            if resp and len(resp) >= 2:
                return resp[1]
            return []
        except Exception:
            return []

    def _make_request(self, params: dict) -> dict | None:
        """发送请求的同步方法"""
        try:
            # 先访问主页获取 cookie
            session = requests.Session()

            # 访问主页
            homepage_url = "https://scavprototype.wiki.gg/zh"
            logger.info(f"[WikiSpider] 访问主页：{homepage_url}")
            session.get(
                homepage_url,
                headers=self.HEADERS,
                timeout=self.timeout,
                impersonate="chrome131"
            )
            time.sleep(0.5)  # 短暂等待

            # 使用带 cookie 的 session 访问 API
            logger.info(f"[WikiSpider] 请求 API URL: {self.BASE_URL}, 参数：{params}")
            resp = session.get(
                self.BASE_URL,
                params=params,
                headers=self.HEADERS,
                timeout=self.timeout,
                impersonate="chrome131"
            )
            logger.info(f"[WikiSpider] 响应状态码：{resp.status_code}")

            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(f"[WikiSpider] 请求失败，状态码：{resp.status_code}")
                logger.error(f"[WikiSpider] 响应内容：{resp.text[:200]}")
                return None

        except Exception as e:
            logger.error(f"[WikiSpider] 请求异常：{str(e)}")
            return None

    async def _request(self, params: dict) -> dict:
        result = self._make_request(params)
        if result:
            return result
        return {"error": "HTTP Error 403"}

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

