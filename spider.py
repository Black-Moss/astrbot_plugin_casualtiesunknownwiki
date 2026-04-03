import aiohttp
from typing import Optional
from curl_cffi import requests


class WikiSpider:
    BASE_URL = "https://scavprototype.wiki.gg/zh/api.php"

    # 使用真实的浏览器 User-Agent
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://scavprototype.wiki.gg/",
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
            # 使用 curl_cffi 发送请求以绕过 Cloudflare，启用 chrome120 模拟
            resp = requests.get(
                self.BASE_URL,
                params=params,
                headers=self.HEADERS,
                timeout=self.timeout,
                impersonate="chrome120"
            )
            resp.raise_for_status()
            data = resp.json()
            if len(data) >= 2:
                return data[1]
            return []
        except Exception:
            return []

    async def _request(self, params: dict) -> dict:
        try:
            logger.info(f"[WikiSpider] 请求 URL: {self.BASE_URL}, 参数：{params}")
            resp = requests.get(
                self.BASE_URL,
                params=params,
                headers=self.HEADERS,
                timeout=self.timeout,
                impersonate="chrome120"
            )
            logger.info(f"[WikiSpider] 响应状态码：{resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"[WikiSpider] 请求失败：{str(e)}")
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

