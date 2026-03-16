import os
import os.path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .spider import WikiSpider
from .cache import CacheManager


@register("stardewvalleywiki", "YourName", "星露谷物语中文维基查询插件", "1.0.0")
class StardewValleyWiki(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.spider = WikiSpider()
        
        # 获取插件数据目录
        data_dir = os.path.join(context.get_data_dir(), "stardewvalleywiki")
        self.cache = CacheManager(data_dir)

    async def initialize(self):
        logger.info("星露谷维基查询插件已加载")

    @filter.command("wiki")
    async def wiki(self, event: AstrMessageEvent):
        """查询星露谷维基"""
        args = event.message_str.strip().split()
        
        if not args:
            yield event.plain_result("请输入查询关键词，如：/wiki 丢失的斧子\n搜索模式：/wiki search 物品名")
            return

        if args[0] == "search":
            yield await self._search(event, args[1:] if len(args) > 1 else [])
        else:
            keyword = " ".join(args)
            yield await self._query(event, keyword)

    async def _query(self, event: AstrMessageEvent, keyword: str):
        """查询页面"""
        cached = self.cache.get_page(keyword)
        if cached:
            logger.info(f"[Wiki] 命中缓存: {keyword}")
            yield event.plain_result(self._format_content(cached))
            return

        logger.info(f"[Wiki] 查询: {keyword}")
        data = self.spider.query_page(keyword)
        
        if "error" in data:
            yield event.plain_result(f"查询失败: {data['error']}")
            return

        result = self.spider.parse_page_content(data)
        if result:
            content = result["content"]
            self.cache.set_page(keyword, content)
            yield event.plain_result(self._format_content(content))
        else:
            yield event.plain_result(f"未找到页面：「{keyword}」")

    async def _search(self, event: AstrMessageEvent, args: list):
        """搜索页面"""
        if not args:
            yield event.plain_result("请输入搜索关键词，如：/wiki search 酿酒")
            return

        keyword = " ".join(args)
        cached = self.cache.get_search(keyword)
        if cached:
            logger.info(f"[Wiki] 搜索命中缓存: {keyword}")
            yield event.plain_result(self._format_search_results(keyword, cached))
            return

        logger.info(f"[Wiki] 搜索: {keyword}")
        results = self.spider.search(keyword)
        
        if results:
            self.cache.set_search(keyword, results)
            yield event.plain_result(self._format_search_results(keyword, results))
        else:
            yield event.plain_result(f"未找到相关结果：「{keyword}」")

    def _format_content(self, content: str) -> str:
        """格式化页面内容"""
        lines = content.split("\n")
        result = []
        in_table = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("{|") or line.startswith("{|"):
                in_table = True
                continue
            if line == "|}" or line == "|}" or line == "|}":
                in_table = False
                continue
            if in_table:
                continue
            if line.startswith("==") and line.endswith("=="):
                result.append(f"\n{line}\n")
            elif line.startswith("===") and line.endswith("==="):
                result.append(f"\n{line}\n")
            elif line.startswith("|") or line.startswith("!"):
                continue
            elif line.startswith("[[") and "]]" in line:
                continue
            elif line.startswith("{{") and "}}" in line:
                continue
            else:
                if line and len(line) > 2:
                    result.append(line)
        
        return "\n".join(result[:50])

    def _format_search_results(self, keyword: str, results: list) -> str:
        """格式化搜索结果"""
        if not results:
            return f"未找到相关结果：「{keyword}」"
        
        msg = f"「{keyword}」相关页面：\n"
        for i, r in enumerate(results[:10], 1):
            msg += f"{i}. {r}\n"
        return msg.strip()
