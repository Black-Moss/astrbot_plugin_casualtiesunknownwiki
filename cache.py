import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class CacheManager:
    CACHE_TTL_HOURS = 24

    def __init__(self, data_dir: Path):
        self.cache_file = data_dir / "casualtiesunknownwiki.json"
        self._ensure_cache_file()

    def _ensure_cache_file(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.cache_file.exists():
            self._save({"pages": {}, "searches": {}, "meta": {}})

    def _load(self) -> dict:
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"pages": {}, "searches": {}, "meta": {}}

    def _save(self, data: dict):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _is_expired(self, timestamp: str) -> bool:
        try:
            update_time = datetime.fromisoformat(timestamp)
            return datetime.now() - update_time > timedelta(hours=self.CACHE_TTL_HOURS)
        except (ValueError, TypeError):
            return True

    def get_page(self, title: str) -> Optional[str]:
        cache = self._load()
        pages = cache.get("pages", {})
        if title in pages:
            page_data = pages[title]
            if not self._is_expired(page_data.get("update_time", "")):
                return page_data.get("content")
            else:
                del pages[title]
                cache["pages"] = pages
                self._save(cache)
        return None

    def set_page(self, title: str, content: str):
        cache = self._load()
        if "pages" not in cache:
            cache["pages"] = {}
        cache["pages"][title] = {
            "content": content,
            "update_time": datetime.now().isoformat()
        }
        self._save(cache)

    def get_search(self, keyword: str) -> Optional[list]:
        cache = self._load()
        searches = cache.get("searches", {})
        if keyword in searches:
            search_data = searches[keyword]
            if not self._is_expired(search_data.get("update_time", "")):
                return search_data.get("results")
            else:
                del searches[keyword]
                cache["searches"] = searches
                self._save(cache)
        return None

    def set_search(self, keyword: str, results: list):
        cache = self._load()
        if "searches" not in cache:
            cache["searches"] = {}
        cache["searches"][keyword] = {
            "results": results,
            "update_time": datetime.now().isoformat()
        }
        self._save(cache)
