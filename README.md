🚀 جستجوگر ویکی‌پدیا (Wikipedia Crawler)

📖 درباره پروژه

این پروژه یک سیستم جستجوگر ویکی‌پدیا با معماری مدرن پایتون است.

این سیستم چه کاری انجام می‌دهد؟

کاربر از طریق یک کلاینت دسکتاپ (Tkinter)، عبارت مورد نظر خود را برای جستجو در ویکی‌پدیا ارسال می‌کند.

یک سرور FastAPI درخواست را دریافت کرده و آن را به صف وظایف (ARQ) می‌سپارد.

یک ورکر (Worker) در پس‌زمینه، وظیفه را برداشته، مقالات را از ویکی‌پدیا واکشی (Crawl) می‌کند.

نتایج (شامل متن کامل مقالات) در یک پایگاه داده PostgreSQL ذخیره می‌شوند.

کاربر می‌تواند نتایج را در کلاینت دسکتاپ مشاهده کند.

🔧 راه‌اندازی (فعال‌سازی)

۱. پیش‌نیازها

Python 3.13+

پکیج منیجر uv (اگر نصب نیست: curl -LsSf https://astral.sh/uv/install.sh | sh)

یک سرور PostgreSQL در حال اجرا

یک سرور Redis در حال اجرا (روی پورت 6379)

۲. کلون کردن مخزن

git clone [https://github.com/hamed-py/web_crawler.git](https://github.com/hamed-py/web_crawler.git)
cd web_crawler


۳. ساخت فایل .env (ضروری)

یک فایل با نام .env در ریشه پروژه بسازید و اطلاعات اتصال به پایگاه داده PostgreSQL خود را در آن وارد کنید:

# .env
# مثال:
DATABASE_URL="postgresql://postgres:mysecretpassword@localhost:5432/crawler_db"


(مطمئن شوید که پایگاه داده crawler_db از قبل در PostgreSQL ساخته شده باشد.)

۴. ایجاد و فعال‌سازی محیط مجازی

# ۱. ساخت محیط مجازی
uv venv


در macOS / Linux:

source .venv/bin/activate


در Windows (PowerShell):

. \.venv\Scripts\Activate.ps1


در Windows (CMD):

.\.venv\Scripts\activate


۵. نصب وابستگی‌ها

# همگام‌سازی سریع با فایل uv.lock
uv pip sync


🖥️ اجرای پروژه

برای اجرای کامل سیستم، سه ترمینال مجزا باز کنید. در هر سه ترمینال، ابتدا محیط مجازی (.venv) را طبق دستور بالا فعال کنید. (همچنین مطمئن شوید سرویس‌های PostgreSQL و Redis شما در حال اجرا هستند).

🏁 ترمینال ۱: اجرای ARQ Worker

(این ترمینال وظایف را از صف برداشته و اجرا می‌کند)

# 
uv run arq server.worker.WorkerSettings


🏁 ترمینال ۲: اجرای FastAPI Server

(این ترمینال API سرور را اجرا می‌کند)

#
uv run uvicorn server.server:app --host 127.0.0.1 --port 8000 --reload


🏁 ترمینال ۳: اجرای کلاینت Tkinter

(این ترمینال رابط کاربری دسکتاپ را اجرا می‌کند)

# 
uv run python client/main.py
