import aiohttp
from typing import Optional
import logging
import json
from astrbot.api import logger
from playwright.async_api import async_playwright


class WikiSpider:
    EN_URL = "https://scavprototype.wiki.gg/api.php"
    ZH_URL = "https://scavprototype.wiki.gg/zh/api.php"

    def __init__(self, timeout: int = 30, cookies: dict = None):
        self.timeout = timeout
        self.cookies = cookies or {}
        
        if not self.cookies:
            import os
            cookie_str = os.environ.get('WIKI_COOKIES', '')
            if cookie_str:
                try:
                    self.cookies = eval(cookie_str)
                except:
                    pass
        
        logger.info(f"[WikiSpider] 初始化完成，当前 cookies: {list(self.cookies.keys()) if self.cookies else '无'}")

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
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
            )
            
            if self.cookies:
                await context.add_cookies([
                    {'name': k, 'value': v, 'domain': 'scavprototype.wiki.gg', 'path': '/'}
                    for k, v in self.cookies.items()
                ])
            
            page = await context.new_page()
            
            # 尝试中文 API
            try:
                zh_url_with_params = f"{self.ZH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
                response = await page.goto(zh_url_with_params, wait_until='networkidle')
                if response.status == 200:
                    data = await response.json()
                    if len(data) >= 2 and data[1]:
                        await browser.close()
                        return data[1]
            except Exception as e:
                logger.warning(f"中文 API 搜索失败：{e}")

            # 尝试英文 API
            try:
                en_url_with_params = f"{self.EN_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
                response = await page.goto(en_url_with_params, wait_until='networkidle')
                if response.status == 200:
                    data = await response.json()
                    if len(data) >= 2 and data[1]:
                        await browser.close()
                        return data[1]
            except Exception as e:
                logger.warning(f"英文 API 搜索失败：{e}")
            
            await browser.close()
            return []

    async def _request(self, params: dict) -> dict:
        async with async_playwright() as p:
            # 启动浏览器（无头模式）
            browser = await p.chromium.launch(headless=True)
            
            # 创建浏览器上下文
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
                viewport={'width': 1920, 'height': 1080}
            )
            
            # 添加 cookies
            if self.cookies:
                await context.add_cookies([
                    {'name': k, 'value': v, 'domain': 'scavprototype.wiki.gg', 'path': '/'}
                    for k, v in self.cookies.items()
                ])
            
            page = await context.new_page()
            
            # 优先尝试中文 API
            try:
                logger.info(f"[WikiSpider] 中文查询：{params}")
                zh_url_with_params = f"{self.ZH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
                response = await page.goto(zh_url_with_params, wait_until='networkidle')
                
                logger.info(f"[WikiSpider] 中文响应状态码：{response.status}")
                
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        data = await response.json()
                        await browser.close()
                        return data
                    else:
                        logger.error(f"[WikiSpider] 中文 API 返回非 JSON 内容：{content_type}")
                else:
                    logger.error(f"[WikiSpider] 中文 API 返回非 200 状态码：{response.status}")
            except Exception as e:
                logger.error(f"[WikiSpider] 中文 API 请求异常：{type(e).__name__}: {e}")

            # 中文失败后尝试英文 API
            try:
                logger.info(f"[WikiSpider] 英文查询：{params}")
                en_url_with_params = f"{self.EN_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
                response = await page.goto(en_url_with_params, wait_until='networkidle')
                
                logger.info(f"[WikiSpider] 英文响应状态码：{response.status}")
                
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        data = await response.json()
                        await browser.close()
                        return data
                    else:
                        logger.error(f"[WikiSpider] 英文 API 返回非 JSON 内容：{content_type}")
                else:
                    logger.error(f"[WikiSpider] 英文 API 返回非 200 状态码：{response.status}")
            except Exception as e:
                logger.error(f"[WikiSpider] 英文 API 请求异常：{type(e).__name__}: {e}")
            
            await browser.close()
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
