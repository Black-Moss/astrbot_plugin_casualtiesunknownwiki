from curl_cffi import requests
from curl_cffi.const import CurlOpt
from typing import Optional
from astrbot.api import logger
import time


class WikiSpider:
    BASE_URL = "https://scavprototype.wiki.gg/zh/api.php"

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
            resp = await self._make_request(params)
            if resp and len(resp) >= 2:
                return resp[1]
            return []
        except Exception:
            return []

    async def _make_request(self, params: dict) -> dict | None:
        """使用更底层的 API 绕过 Cloudflare"""
        try:
            from curl_cffi import Curl
            
            curl = Curl()
            
            # 设置浏览器特征
            curl.setopt(CurlOpt.USERAGENT, b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
            curl.setopt(CurlOpt.HTTP_VERSION, 2)
            
            # 构建 URL
            url = f"{self.BASE_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
            logger.info(f"[WikiSpider] 请求 URL: {url}")
            
            # 设置 TLS 指纹
            curl.setopt(CurlOpt.SSL_EC_CURVES, b"x25519kyber768draft00")
            
            resp = curl.perform(url)
            status_code = curl.getinfo(CurlInfo.RESPONSE_CODE)
            content = resp.decode('utf-8')
            
            logger.info(f"[WikiSpider] 响应状态码：{status_code}")
            
            if status_code == 200:
                import json
                return json.loads(content)
            else:
                logger.error(f"[WikiSpider] 请求失败，状态码：{status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[WikiSpider] 请求异常：{str(e)}")
            return None

    async def _request(self, params: dict) -> dict:
        result = await self._make_request(params)
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

