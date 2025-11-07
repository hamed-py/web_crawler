import redis.asyncio as redis
from arq.connections import RedisSettings

from shared.database import AsyncSessionLocal, WikipediaArticle
from .crawler import WikipediaCrawler, DataSaverAsync


async def run_crawl_task(ctx, task_details: dict):
    """تابع اصلی اجرای تسک در ورکر."""
    crawler_name = task_details.get("crawler_name")
    params = task_details.get("params", {})

    print(f"Worker received job: {ctx['job_id']} for crawler: {crawler_name} with params: {params}")

    crawler_instance = None
    model_class = None

    try:

        if crawler_name == "wikipedia":
            search_term = params.get("search_term")
            if not search_term:
                raise ValueError("search_term (عبارت جستجو) الزامی است")
            crawler_instance = WikipediaCrawler(search_term=search_term)
            model_class = WikipediaArticle

        else:
            raise ValueError(f"کراولر ناشناخته: {crawler_name}")


        async with AsyncSessionLocal() as db:

            items = await crawler_instance.run()
            if items:
                saver = DataSaverAsync(db_session=db)
                count = await saver.save_items(items, model_class)
                return {"status": "success", "found": len(items), "saved": count}
            else:
                return {"status": "success", "found": 0, "saved": 0}

    except Exception as e:
        print(f"Job {ctx['job_id']} failed: {e}")
        return {"status": "failed", "error": str(e)}

    finally:
        if crawler_instance:
            await crawler_instance.close()
        print(f"Worker finished job: {ctx['job_id']}")


REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
redis_settings = RedisSettings(host=REDIS_HOST, port=REDIS_PORT)


async def startup(ctx):
    """تابع راه‌اندازی ورکر."""
    print(f"ARQ Worker starting up, connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    ctx['redis'] = await redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}")
    print("ARQ Worker started successfully.")


async def shutdown(ctx):
    print("ARQ Worker shutting down...")
    await ctx['redis'].close()



class WorkerSettings:
    functions = [run_crawl_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings