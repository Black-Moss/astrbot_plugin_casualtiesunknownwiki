from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger

from .spider import WikiSpider
from .cache import CacheManager


@register("casualtiesunknownwiki", "Black_Moss", "Casualties Unknown Wiki 查询", "1.0.0")
class CasualtiesUnknownWiki(Star):
    def __init__(self, context: Context, config: Config):
        super().__init__(context)

        self.spider = WikiSpider(cookies=cookies)
        data_dir = StarTools.get_data_dir()
        self.config = config
        if not cookies:
            logger.warning("[Wiki] 未配置 wiki_cookies，可能无法通过 Cloudflare 验证")
        self.cache = CacheManager(data_dir)


    async def initialize(self):
        logger.info("Casualties Unknown Wiki 查询已加载")

    @filter.command("wiki")
    async def wiki(self, event: AstrMessageEvent):
        args = event.message_str.strip().split()
        args = args[1:] if args and args[0] in ["wiki", "/wiki"] else args
        
        if not args:
            yield event.plain_result("请输入查询关键词，如：/wiki 设定\n搜索模式：/wiki search 物品名")
            return

        if args[0] == "search":
            result = await self._search(event, args[1:] if len(args) > 1 else [])
            if result:
                yield event.plain_result(result)
        else:
            keyword = " ".join(args)
            result = await self._query(event, keyword)
            if result:
                yield event.plain_result(result)

    async def _query(self, event: AstrMessageEvent, keyword: str) -> str | None:
        cached = self.cache.get_page(keyword)
        if cached:
            logger.info(f"[Wiki] 命中缓存：{keyword}")
            return self._format_content(cached)

        logger.info(f"[Wiki] 查询：{keyword}")
        data = await self.spider.query_page(keyword)
        
        if "error" in data:
            return f"查询失败：{data['error']}"

        result = self.spider.parse_page_content(data)
        if result:
            content = result["content"]
            self.cache.set_page(keyword, content)
            return self._format_content(content)
        else:
            return f"未找到页面：「{keyword}」"

    async def _search(self, event: AstrMessageEvent, args: list) -> str | None:
        if not args:
            return "请输入搜索关键词，如：/wiki search 酿酒"

        keyword = " ".join(args)
        cached = self.cache.get_search(keyword)
        if cached:
            logger.info(f"[Wiki] 搜索命中缓存：{keyword}")
            return self._format_search_results(keyword, cached)

        logger.info(f"[Wiki] 搜索：{keyword}")
        results = await self.spider.search(keyword)
        
        if results:
            self.cache.set_search(keyword, results)
            return self._format_search_results(keyword, results)
        else:
            return f"未找到相关结果：「{keyword}」"

    def _format_content(self, content: str) -> str:
        lines = content.split("\n")
        result = []
        in_table = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("{|"):
                in_table = True
                continue
            if line == "|}" or line == "|}}":
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
        if not results:
            return f"未找到相关结果：「{keyword}」"
        
        msg = f"「{keyword}」相关页面：\n"
        for i, r in enumerate(results[:10], 1):
            msg += f"{i}. {r}\n"
        return msg.strip()
