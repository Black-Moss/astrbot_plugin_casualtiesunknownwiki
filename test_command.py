import asyncio
from spider import WikiSpider
from cache import CacheManager
import sys
sys.path.insert(0, 'D:/Program/astrbot_plugin_stardewvalleywiki')

class MockEvent:
    def __init__(self, message_str):
        self.message_str = message_str

class MockStarTools:
    @staticmethod
    def get_data_dir():
        return "./data"

# 模拟 main.py 的逻辑
def test_command(message_str):
    print(f"\n=== 测试命令: '{message_str}' ===")
    args = message_str.strip().split()
    print(f"args = {args}")
    
    if args[0] == "search":
        keyword = " ".join(args[1:]) if len(args) > 1 else ""
        print(f"搜索模式, keyword = '{keyword}'")
    else:
        keyword = " ".join(args)
        print(f"查询模式, keyword = '{keyword}'")

# 测试各种输入
test_command("search 胡萝卜")
test_command("wiki search 胡萝卜")
test_command("/wiki search 胡萝卜")
test_command("wiki 胡萝卜")
