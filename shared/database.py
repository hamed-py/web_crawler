import os
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found in .env file")

# اتصال آسنکرون (برای FastAPI و ARQ)
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
AsyncEngine = create_async_engine(ASYNC_DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=AsyncEngine, expire_on_commit=False)

# اتصال سنکرون (برای کلاینت Tkinter)
SyncEngine = create_engine(DATABASE_URL)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=SyncEngine)



class Base(DeclarativeBase):

    __unique_constraint_column__ = None



class WikipediaArticle(Base):

    __tablename__ = "wikipedia_articles"

    __unique_constraint_column__ = "pageid"

    id = Column(Integer, primary_key=True, index=True)
    pageid = Column(Integer, unique=True, index=True)
    title = Column(String(500), index=True)
    summary = Column(Text)
    url = Column(String(1000), nullable=True)
    full_text = Column(Text, nullable=True)

    def __repr__(self):
        return f"<WikipediaArticle(pageid={self.pageid}, title='{self.title[:30]}...')>"



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