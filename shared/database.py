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



ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
AsyncEngine = create_async_engine(ASYNC_DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=AsyncEngine, expire_on_commit=False)


SyncEngine = create_engine(DATABASE_URL)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=SyncEngine)


class Base(DeclarativeBase):
    
    __unique_constraint_column__ = None

class Quote(Base):
    __tablename__ = "quotes"
    __unique_constraint_column__ = "text" # این متن یونیک است
    
    id = Column(Integer, primary_key=True, index=True)
    author = Column(String(255), index=True)
    text = Column(Text, nullable=False, unique=True) # اضافه کردن unique=True

    def __repr__(self):
        return f"<Quote(author='{self.author}')>"

class DivarListing(Base):
    __tablename__ = "divar_listings"
    __unique_constraint_column__ = "token" # توکن یونیک است
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500))
    price = Column(String(100), default="توافقی")
    token = Column(String(100), unique=True, index=True) 

    @property
    def url(self):
        return f"https://divar.ir/v/--/{self.token}"

    def __repr__(self):
        return f"<DivarListing(title='{self.title[:30]}...')>"

# --- توابع مدیریت دیتابیس ---

async def create_db_and_tables_async():
    async with AsyncEngine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Async: Database tables created.")

def create_db_and_tables_sync():
    Base.metadata.create_all(bind=SyncEngine)
    print("Sync: Database tables created.")

# Dependency برای FastAPI
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session