from curl_cffi import requests
from typing import Optional
from astrbot.api import logger


class WikiSpider:
    BASE_URL = "https://scavprototype.wiki.gg/zh/api.php"
    
    # 如果您有 Bot Token，在这里配置
    BOT_TOKEN = None  # 例如："your_bot_token_here"

    HEADERS = {
        "User-Agent": "CasualtiesUnknownWikiBot/1.0 (Contact: your_email@example.com)",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        
        if self.BOT_TOKEN:
            self.HEADERS["Authorization"] = f"Bearer {self.BOT_TOKEN}"

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
        try:
            logger.info(f"[WikiSpider] 请求 URL: {self.BASE_URL}, 参数：{params}")
            
            resp = requests.get(
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
                logger.error(f"[WikiSpider] 响应头：{dict(resp.headers)}")
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

