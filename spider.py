import requests


from typing import Optional


class WikiSpider:
    """星露谷中文维基爬虫"""

    BASE_URL = "https://zh.stardewvalleywiki.com/mediawiki/api.php"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def query_page(self, title: str, redirects: bool = True) -> dict:
        """查询单个页面"""
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "revisions",
            "rvprop": "content",
            "redirects": 1 if redirects else 0
        }
        return self._request(params)

    def search(self, keyword: str, limit: int = 10) -> list:
        """搜索页面"""
        params = {
            "action": "opensearch",
            "format": "json",
            "search": keyword,
            "limit": limit
        }
        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if len(data) >= 2:
                return data[1]
            return []
        except Exception as e:
            return []

    def _request(self, params: dict) -> dict:
        """发送请求"""
        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def parse_page_content(data: dict) -> Optional[dict]:
        """解析页面内容"""
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
