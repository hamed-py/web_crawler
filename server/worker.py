
import asyncio
import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings

# وارد کردن کلاس‌های کراولر و ذخیره‌ساز از فایل crawler.py
from .crawler import QuoteCrawler, DivarCrawler, DataSaverAsync
# وارد کردن سشن دیتابیس و مدل‌ها
from shared.database import AsyncSessionLocal, Quote, DivarListing



async def run_crawl_task(ctx, crawler_name: str):
    
    print(f"Worker received job: {ctx['job_id']} for crawler: {crawler_name}")
    
    crawler_instance = None
    model_class = None

   
    if crawler_name == "quotes":
        crawler_instance = QuoteCrawler()
        model_class = Quote
    elif crawler_name == "divar_laptops":
        crawler_instance = DivarCrawler(city="tehran", category="laptop-notebook")
        model_class = DivarListing
    # مثال:
    # elif crawler_name == "bama_cars":
    #     crawler_instance = BamaCrawler()
    #     model_class = BamaListing
    else:
        raise ValueError(f"Unknown crawler_name: {crawler_name}")

    
    async with AsyncSessionLocal() as db:
        try:
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


REDIS_HOST = "localhost"
REDIS_PORT = 6379
redis_settings = RedisSettings(host=REDIS_HOST, port=REDIS_PORT)

async def startup(ctx):
    """تابع راه‌اندازی ورکر."""
    print(f"ARQ Worker starting up, connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    # ایجاد یک کلاینت Redis برای استفاده در سرور FastAPI
    ctx['redis'] = await redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}")
    print("ARQ Worker started successfully.")

async def shutdown(ctx):
    """تابع خاموش شدن ورکر."""
    print("ARQ Worker shutting down...")
    await ctx['redis'].close()

# تعریف کلاس ورکر
class WorkerSettings:
    functions = [run_crawl_task] 
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings