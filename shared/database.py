import os
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

# بارگیری متغیرهای محیطی از فایل .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found in .env file")

# --- اتصالات دیتابیس ---

# اتصال آسنکرون (برای FastAPI و ARQ)
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
AsyncEngine = create_async_engine(ASYNC_DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=AsyncEngine, expire_on_commit=False)

# اتصال سنکرون (برای کلاینت Tkinter)
SyncEngine = create_engine(DATABASE_URL)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=SyncEngine)


# --- مدل‌های پایه ---

class Base(DeclarativeBase):
    """
    کلاس پایه Declarative که ستون یونیک پیش‌فرض را برای DataSaver تعریف می‌کند.
    """
    __unique_constraint_column__ = None


# مدل Quote حذف شد

class WikipediaArticle(Base):
    """[بهبود یافته] مدل جدید برای ذخیره مقالات ویکی‌پدیا"""
    __tablename__ = "wikipedia_articles"
    # از pageid برای جلوگیری از تکرار استفاده می‌کنیم
    __unique_constraint_column__ = "pageid"

    id = Column(Integer, primary_key=True, index=True)
    pageid = Column(Integer, unique=True, index=True)  # شناسه صفحه در ویکی‌پدیا
    title = Column(String(500), index=True)
    summary = Column(Text)  # خلاصه‌ای که از API جستجو می‌آید
    url = Column(String(1000), nullable=True) # URL کامل مقاله
    full_text = Column(Text, nullable=True) # متن کامل مقاله (در صورت واکشی)

    def __repr__(self):
        return f"<WikipediaArticle(pageid={self.pageid}, title='{self.title[:30]}...')>"


# --- توابع مدیریت دیتابیس ---

async def create_db_and_tables_async():
    """جداول را به صورت آسنکرون (برای سرور) ایجاد می‌کند."""
    async with AsyncEngine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Async: Database tables created (only wikipedia_articles).")


def create_db_and_tables_sync():
    """جداول را به صورت سنکرون (برای کلاینت) ایجاد می‌کند."""
    Base.metadata.create_all(bind=SyncEngine)
    print("Sync: Database tables created (only wikipedia_articles).")



async def get_async_db():
    """یک سشن دیتابیس Async در اختیار endpoint های FastAPI قرار می‌دهد."""
    async with AsyncSessionLocal() as session:
        yield session