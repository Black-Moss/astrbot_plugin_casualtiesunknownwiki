import asyncio
from spider import WikiSpider

async def test():
    spider = WikiSpider()
    
    print("=== 测试搜索 ===")
    results = await spider.search("胡萝卜")
    print("搜索 '胡萝卜' 结果:", results)
    
    print("\n=== 测试查询 ===")
    page = await spider.query_page("胡萝卜")
    if "error" in page:
        print("查询失败:", page["error"])
    else:
        result = spider.parse_page_content(page)
        if result:
            print("查询成功:", result["title"])
            print("内容前200字:", result["content"][:200])
        else:
            print("未找到页面")

asyncio.run(test())
