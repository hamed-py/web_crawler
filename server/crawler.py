import httpx
import asyncio
import json
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from shared.database import Quote, DivarListing



class BaseCrawler:
    
    def __init__(self, base_url: str, concurrency_limit: int = 5):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
            http2=True,
            timeout=10.0
        )
        # بهبود حیاتی: اعمال محدودیت همزمانی برای جلوگیری از بن شدن
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        print(f"Async Crawler for {base_url} initialized (Concurrency: {concurrency_limit}).")

    async def fetch_page(self, url_path: str = "") -> str | None:
        """محتوای صفحه را به صورت ناهمزمان و کنترل شده واکشی می‌کند."""
        async with self.semaphore:
            try:
                print(f"Fetching {url_path}...")
                response = await self.client.get(url_path)
                response.raise_for_status()
                return response.text
            except httpx.RequestError as e:
                print(f"HTTP Error fetching {e.request.url!r}: {e}")
                return None

    async def parse(self, content: str) -> list:
        raise NotImplementedError("Subclass must implement abstract method parse")

    async def run(self) -> list:
        content = await self.fetch_page()
        if content:
            return await self.parse(content)
        return []

    async def close(self):
        """کلاینت http را می‌بندد."""
        await self.client.aclose()


class QuoteCrawler(BaseCrawler):
    """کراولر آسنکرون برای نقل قول‌ها."""
    def __init__(self):
        # محدودیت همزمانی 2، چون سایت تست ضعیف است
        super().__init__(base_url="http://quotes.toscrape.com", concurrency_limit=2)

    async def parse(self, html_content: str) -> list[dict]:
        print("Parsing quotes...")
        soup = BeautifulSoup(html_content, "html.parser")
        quotes_data = []
        for q in soup.find_all("div", class_="quote"):
            text = q.find("span", class_="text").get_text(strip=True)
            author = q.find("small", class_="author").get_text(strip=True)
            quotes_data.append({"text": text, "author": author})
        print(f"Found {len(quotes_data)} quotes.")
        return quotes_data

class DivarCrawler(BaseCrawler):
    """کراولر مدرن برای دیوار با استفاده از JSON API."""
    def __init__(self, city="tehran", category="laptop-notebook"):
        base_url = f"https://api.divar.ir/v8/web-search/{city}/{category}"
        # محدودیت همزمانی 5
        super().__init__(base_url=base_url, concurrency_limit=5)

    async def parse(self, json_content: str) -> list[dict]:
        print("Parsing Divar JSON API...")
        try:
            data = json.loads(json_content)
            listings = []
            for widget in data.get("widget_list", []):
                post_data = widget.get("data", {})
                if "token" in post_data and "title" in post_data:
                    price = "توافقی"
                    for p_key in ("price_text", "subtitle"):
                        if p_key in post_data:
                            price = post_data[p_key]
                            break
                    listings.append({
                        "token": post_data.get("token"),
                        "title": post_data.get("title"),
                        "price": price,
                    })
            print(f"Found {len(listings)} Divar listings.")
            return listings
        except json.JSONDecodeError:
            print("Error: Failed to decode Divar JSON response.")
            return []

# --- کلاس ذخیره‌ساز آسنکرون (بهبود یافته) ---

class DataSaverAsync:
    """مسئول ذخیره ناهمزمان داده‌ها با استفاده از ستون یونیک داینامیک."""
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def save_items(self, items: list[dict], model_class):
        if not items:
            return 0

        # بهبود: خواندن ستون یونیک به صورت داینامیک از خود مدل
        constraint_column = getattr(model_class, '__unique_constraint_column__', None)
        if not constraint_column:
            raise TypeError(f"Model {model_class.__name__} does not have __unique_constraint_column__ defined.")

        stmt = insert(model_class).values(items)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[constraint_column]
        )
        
        try:
            result = await self.db.execute(stmt)
            await self.db.commit()
            print(f"Successfully saved {result.rowcount} new items to {model_class.__tablename__}.")
            return result.rowcount
        except Exception as e:
            await self.db.rollback()
            print(f"Error saving to DB: {e}")
            return 0