from typing import List, Dict, Any, Optional
import redis.asyncio as redis
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from arq.jobs import Job
from fastapi import FastAPI, Depends, HTTPException
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from shared import database
from .worker import REDIS_HOST, REDIS_PORT

# [اصلاح] عنوان برنامه فارسی شد
app = FastAPI(title="API جستجوگر ویکی‌پدیا", version="5.0")


# QuoteSchema حذف شد

class WikipediaArticleSchema(BaseModel):
    """[بهبود یافته] اسکیمای Pydantic برای مقالات ویکی‌پدیا"""
    id: int
    pageid: int
    title: str
    summary: str
    url: Optional[str] = None
    full_text: Optional[str] = None

    class Config: from_attributes = True


class CrawlRequest(BaseModel):
    """[بدون تغییر] مدل درخواست ارسال Job"""
    crawler_name: str
    params: Dict[str, Any] = {}


class JobResponse(BaseModel):
    """[بدون تغییر] مدل پاسخ ارسال Job"""
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    """[بدون تغییر] مدل وضعیت Job"""
    status: str
    result: dict | None = None


# --- بخش مدیریت رویدادهای FastAPI (بدون تغییر) ---

arq_pool: ArqRedis = None

@app.on_event("startup")
async def startup_event():
    print("FastAPI server starting up (v5.0 - Wikipedia Only)...")
    await database.create_db_and_tables_async()

    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    redis_client = await redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_client)
    print("FastAPI-Limiter connected to Redis.")

    global arq_pool
    arq_pool = await create_pool(RedisSettings(host=REDIS_HOST, port=REDIS_PORT))
    print("ARQ pool created for job enqueueing.")


@app.on_event("shutdown")
async def shutdown_event():
    await FastAPILimiter.close()
    if arq_pool:
        await arq_pool.close()
    print("FastAPI server shut down gracefully.")


# --- اندپوینت‌های API ---

@app.get("/", summary="Root Endpoint")
async def read_root():
    """[اصلاح] پیام خوشامدگویی فارسی شد"""
    return {"message": "به API جستجوگر سازمانی ویکی‌پدیا خوش آمدید (نسخه 5.0)."}


@app.post(
    "/jobs/crawl",
    response_model=JobResponse,
    summary="ثبت یک درخواست جستجوی جدید",
    dependencies=[Depends(RateLimiter(times=2, minutes=1))]  # محدودیت 2 درخواست در دقیقه
)
async def submit_crawl_job(request: CrawlRequest):
    """
    [اصلاح] این اندپوینت اکنون فقط درخواست‌های 'wikipedia' را می‌پذیرد (کنترل در ورکر انجام می‌شود).
    """
    if not arq_pool:
        raise HTTPException(status_code=503, detail="صف کارها در دسترس نیست")

    task_details = request.dict()

    job = await arq_pool.enqueue_job(
        'run_crawl_task',
        task_details
    )
    return JobResponse(
        job_id=job.job_id,
        status="queued",
        message=f"درخواست برای '{request.crawler_name}' در صف قرار گرفت."
    )


@app.get(
    "/jobs/status/{job_id}",
    response_model=JobStatus,
    summary="بررسی وضعیت یک درخواست جستجو"
)
async def get_job_status(job_id: str):
    """
    وضعیت یک Job را با استفاده از job_id آن بررسی می‌کند. (بدون تغییر)
    """
    if not arq_pool:
        raise HTTPException(status_code=503, detail="صف کارها در دسترس نیست")

    try:
        job = Job(job_id, arq_pool)
        status = await job.status()
        result = None
        if status == "complete":
            result = await job.result()
        elif status == "failed":
            result = await job.result(exc_deserializer=None)

        return JobStatus(status=status, result=result)

    except Exception as e:
        return JobStatus(status="not_found", result={"error": str(e)})



@app.get("/articles", response_model=List[WikipediaArticleSchema], summary="دریافت تمام مقالات ویکی‌پدیا")
async def get_all_articles(db: AsyncSession = Depends(database.get_async_db)):
    query = select(database.WikipediaArticle).order_by(database.WikipediaArticle.id.desc())
    result = await db.execute(query)
    return result.scalars().all()