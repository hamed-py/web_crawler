import asyncio
import json
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


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
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        print(f"Async Crawler for {base_url} initialized (Concurrency: {concurrency_limit}).")

    async def fetch_page(self, url_path: str = "", params: dict = None) -> str | None:
        async with self.semaphore:
            try:
                print(f"Fetching {url_path} with params {params}...")
                response = await self.client.get(url_path, params=params)
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
        await self.client.aclose()



class WikipediaCrawler(BaseCrawler):

    def __init__(self, search_term: str):
        self.search_term = search_term
        super().__init__(base_url="https://en.wikipedia.org", concurrency_limit=5)

    async def run(self) -> list:

        api_path = "/w/api.php"

        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": self.search_term,
            "srlimit": 20
        }
        search_json_content = await self.fetch_page(url_path=api_path, params=search_params)
        if not search_json_content:
            return []

        search_results = await self.parse_search_results(search_json_content)
        if not search_results:
            return []


        page_ids = [item["pageid"] for item in search_results if "pageid" in item]
        if not page_ids:
            return search_results

        details_json_content = await self.fetch_article_details(page_ids)
        if not details_json_content:
            return search_results

        details_map = await self.parse_article_details(details_json_content)


        final_articles = []
        for item in search_results:
            page_id = item["pageid"]
            if page_id in details_map:
                item.update(details_map[page_id])
            final_articles.append(item)

        return final_articles

    async def parse_search_results(self, json_content: str) -> list[dict]:

        print(f"Parsing Wikipedia JSON API for '{self.search_term}'...")
        try:
            data = json.loads(json_content)
            articles = []
            search_results = data.get("query", {}).get("search", [])

            for item in search_results:
                title = item.get("title")
                snippet_html = item.get("snippet")
                pageid = item.get("pageid")

                cleaned_summary = BeautifulSoup(snippet_html, "html.parser").get_text(strip=True)

                if title and cleaned_summary and pageid:
                    articles.append({
                        "pageid": pageid,
                        "title": title,
                        "summary": cleaned_summary,
                    })
            print(f"Found {len(articles)} Wikipedia articles from search.")
            return articles
        except (json.JSONDecodeError, AttributeError):
            print("Error: Failed to decode or parse Wikipedia search response.")
            return []

    async def fetch_article_details(self, page_ids: list[int]) -> str | None:

        print(f"Fetching full details for {len(page_ids)} page IDs...")
        api_path = "/w/api.php"
        details_params = {
            "action": "query",
            "format": "json",
            "pageids": "|".join(map(str, page_ids)),
            "prop": "extracts|info",
            "inprop": "url",
            "exintro": False,
            "explaintext": True,
        }
        return await self.fetch_page(url_path=api_path, params=details_params)

    async def parse_article_details(self, json_content: str) -> dict:

        details_map = {}
        try:
            data = json.loads(json_content)
            pages = data.get("query", {}).get("pages", {})

            for page_id_str, page_data in pages.items():
                page_id = int(page_id_str)
                details_map[page_id] = {
                    "full_text": page_data.get("extract"),
                    "url": page_data.get("fullurl")
                }
            print(f"Parsed full details for {len(details_map)} articles.")
            return details_map
        except (json.JSONDecodeError, AttributeError):
            print("Error: Failed to decode or parse Wikipedia details response.")
            return {}


class DataSaverAsync:

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def save_items(self, items: list[dict], model_class):
        """آیتم‌ها را در دیتابیس ذخیره می‌کند و از درج تکراری جلوگیری می‌کند."""
        if not items:
            return 0

        constraint_column = getattr(model_class, '__unique_constraint_column__', None)
        if not constraint_column:
            raise TypeError(f"Model {model_class.__name__} does not have __unique_constraint_column__ defined.")

        # ساخت کوئری INSERT
        stmt = insert(model_class).values(items)

        stmt = stmt.on_conflict_do_nothing(
            index_elements=[constraint_column]
        ).returning(model_class.id)

        try:
            result = await self.db.execute(stmt)
            inserted_rows = result.scalars().all()
            await self.db.commit()
            count = len(inserted_rows)

            print(f"Successfully saved {count} new items to {model_class.__tablename__}.")
            return count

        except Exception as e:
            await self.db.rollback()
            print(f"Error saving to DB: {e}")
            return 0