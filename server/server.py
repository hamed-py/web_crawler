from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List
import redis.asyncio as redis
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from shared import database
from . import crawler
from .worker import REDIS_HOST, REDIS_PORT 

app = FastAPI(title="Enterprise Crawler API (v3.0)", version="3.0")


class QuoteSchema(database.Quote.__pydantic_model__ = None, BaseModel):
    id: int
    author: str
    text: str
    class Config: from_attributes = True

class DivarListingSchema(database.DivarListing.__pydantic_model__ = None, BaseModel):
    id: int
    title: str
    price: str
    url: str
    class Config: from_attributes = True

class CrawlRequest(BaseModel):
    crawler_name: str # ورودی "عمومی" ما

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatus(BaseModel):
    status: str
    result: dict | None = None


# --- مدیریت اتصال Redis و ARQ ---
arq_pool: ArqRedis = None

@app.on_event("startup")
async def startup_event():
   
    print("FastAPI server starting up...")
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



@app.get("/", summary="Root Endpoint")
async def read_root():
    return {"message": "Welcome to the Enterprise Crawler API."}


@app.post(
    "/jobs/crawl", 
    response_model=JobResponse, 
    summary="Submit a new crawl job",
    dependencies=[Depends(RateLimiter(times=2, minutes=1))] 
)
async def submit_crawl_job(request: CrawlRequest):
    
    if not arq_pool:
        raise HTTPException(status_code=503, detail="Job queue is not available")

    # ارسال کار به ورکر
    job = await arq_pool.enqueue_job(
        'run_crawl_task', # نام تابع در worker.py
        request.crawler_name
    )
    return JobResponse(
        job_id=job.job_id,
        status="queued",
        message=f"Job for '{request.crawler_name}' has been queued."
    )

@app.get(
    "/jobs/status/{job_id}", 
    response_model=JobStatus, 
    summary="Check the status of a crawl job"
)
async def get_job_status(job_id: str):
    """وضعیت یک کار را با job_id آن بررسی می‌کند."""
    if not arq_pool:
        raise HTTPException(status_code=503, detail="Job queue is not available")
        
    job = await arq_pool.job_result(job_id)
    
    if job.status == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(
        status=job.status,
        result=job.result if job.status == "complete" else None
    )

# --- بخش خواندن داده‌ها (بدون تغییر) ---

@app.get("/quotes", response_model=List[QuoteSchema], summary="Get all quotes")
async def get_all_quotes(db: AsyncSession = Depends(database.get_async_db)):
    query = select(database.Quote).order_by(database.Quote.id.desc())
    result = await db.execute(query)
    return result.scalars().all()

@app.get("/listings", response_model=List[DivarListingSchema], summary="Get all Divar listings")
async def get_all_listings(db: AsyncSession = Depends(database.get_async_db)):
    query = select(database.DivarListing).order_by(database.DivarListing.id.desc())
    result = await db.execute(query)
    return result.scalars().all()