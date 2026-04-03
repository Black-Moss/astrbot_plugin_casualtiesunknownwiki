import aiohttp
from typing import Optional
import logging
from astrbot.api import logger
from curl_cffi import requests as curl_requests
import subprocess
import json
import asyncio


class WikiSpider:
    EN_URL = "https://scavprototype.wiki.gg/api.php"
    ZH_URL = "https://scavprototype.wiki.gg/zh/api.php"

    def __init__(self, timeout: int = 30, cookies: dict = None):
        self.timeout = timeout
        self.cookies = cookies or {}
        
        # 如果没有提供 cookies，尝试从环境变量读取
        if not self.cookies:
            import os
            cookie_str = os.environ.get('WIKI_COOKIES', '')
            if cookie_str:
                try:
                    self.cookies = eval(cookie_str)
                except:
                    pass
        
        logger.info(f"[WikiSpider] 初始化完成，当前 cookies: {list(self.cookies.keys()) if self.cookies else '无'}")
        
        # 使用最新支持的 Chrome 版本模拟
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
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "cache-control": "max-age=0",
            "priority": "u=0, i",
            "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
        }
        
        request_cookies = self.cookies.copy() if self.cookies else {}
        return self.session.get(url, params=params, headers=headers, cookies=request_cookies)

    async def _request(self, params: dict) -> dict:
        # 始终使用 subprocess 调用 curl
        return await self._request_with_curl(params)

    async def _request_with_curl(self, params: dict) -> dict:
        """使用 subprocess 调用 curl 命令"""
        
        def _run_curl(url: str) -> tuple[int, str]:
            # 构建 curl 命令
            cmd = ['curl', url, '-G']
            
            # 添加参数
            for key, value in params.items():
                cmd.extend(['--data-urlencode', f'{key}={value}'])
            
            # 添加请求头
            headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "cache-control": "max-age=0",
                "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
            }
            
            for key, value in headers.items():
                cmd.extend(['-H', f'{key}: {value}'])
            
            # 添加 cookies
            if self.cookies:
                cookie_str = '; '.join([f'{k}={v}' for k, v in self.cookies.items()])
                logger.info(f"[WikiSpider] 使用 cookies: {cookie_str[:50]}...")
                cmd.extend(['-b', cookie_str])
            
            logger.info(f"[WikiSpider] 执行 curl 命令：{' '.join(cmd[:5])}...")
            
            # 执行命令
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
                logger.info(f"[WikiSpider] curl 返回码：{result.returncode}")
                if result.returncode != 0:
                    logger.error(f"[WikiSpider] curl stderr: {result.stderr[:200]}")
                return result.returncode, result.stdout
            except subprocess.TimeoutExpired:
                logger.error(f"[WikiSpider] curl 超时")
                return -1, ""
            except Exception as e:
                logger.error(f"curl 执行失败：{e}")
                return -1, ""
        
        # 优先尝试中文 API
        try:
            logger.info(f"[WikiSpider] 中文查询：{params}")
            loop = asyncio.get_event_loop()
            code, output = await loop.run_in_executor(None, _run_curl, self.ZH_URL)
            
            if code == 0 and output.strip():
                logger.info(f"[WikiSpider] 中文查询成功，响应长度：{len(output)}")
                # 输出前 500 字节用于调试
                logger.info(f"[WikiSpider] 中文响应前 500 字节：{output[:500]}")
                try:
                    return json.loads(output)
                except json.JSONDecodeError as e:
                    logger.error(f"[WikiSpider] JSON 解析失败：{e}")
                    # 尝试检测是否为 HTML
                    if output.strip().startswith('<!DOCTYPE') or output.strip().startswith('<html'):
                        logger.error("[WikiSpider] 返回的是 HTML 而非 JSON")
                    raise
            else:
                logger.error(f"[WikiSpider] 中文查询失败，返回码：{code}")
        except Exception as e:
            logger.error(f"[WikiSpider] 中文 API 请求异常：{type(e).__name__}: {e}")

        # 中文失败后尝试英文 API
        try:
            logger.info(f"[WikiSpider] 英文查询：{params}")
            loop = asyncio.get_event_loop()
            code, output = await loop.run_in_executor(None, _run_curl, self.EN_URL)
            
            if code == 0 and output.strip():
                logger.info(f"[WikiSpider] 英文查询成功，响应长度：{len(output)}")
                # 输出前 500 字节用于调试
                logger.info(f"[WikiSpider] 英文响应前 500 字节：{output[:500]}")
                try:
                    return json.loads(output)
                except json.JSONDecodeError as e:
                    logger.error(f"[WikiSpider] JSON 解析失败：{e}")
                    # 尝试检测是否为 HTML
                    if output.strip().startswith('<!DOCTYPE') or output.strip().startswith('<html'):
                        logger.error("[WikiSpider] 返回的是 HTML 而非 JSON")
                    raise
            else:
                logger.error(f"[WikiSpider] 英文查询失败，返回码：{code}")
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
