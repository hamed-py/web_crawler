🚀 جستجوگر ویکی‌پدیا (Wikipedia Crawler)

این پروژه یک سیستم کامل جستجو و واکشی اطلاعات از ویکی‌پدیا است که با معماری مدرن پایتون پیاده‌سازی شده است. سیستم از یک بک‌اند Asynchronous مبتنی بر FastAPI برای مدیریت API، یک صف وظایف (Task Queue) قدرتمند با ARQ برای اجرای جستجوها در پس‌زمینه، و یک کلاینت دسکتاپ Tkinter برای مدیریت و نمایش نتایج تشکیل شده است.

🏛️ معماری سیستم

این پروژه از یک معماری چندلایه و غیرمتمرکز برای تفکیک مسئولیت‌ها و افزایش کارایی استفاده می‌کند:

FastAPI Server (server/server.py):

مسئول دریافت درخواست‌های HTTP از کلاینت [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/server.py].

پیاده‌سازی Rate Limiting (محدودیت ۲ درخواست در دقیقه) با استفاده از fastapi-limiter [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/server.py].

ثبت وظایف (Jobs) جدید در صف Redis برای پردازش توسط ورکر با استفاده از arq_pool.enqueue_job [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/server.py].

ارائه API برای بررسی وضعیت وظایف (/jobs/status/{job_id}) و دریافت نتایج ذخیره شده (/articles) [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/server.py].

ARQ Worker (server/worker.py):

یک پردازشگر پس‌زمینه که به صف Redis (روی پورت 6379) گوش می‌دهد [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/worker.py].

وظایف جستجو (run_crawl_task) را از صف برداشته و اجرا می‌کند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/worker.py].

از WikipediaCrawler برای جستجو و واکشی متن کامل مقالات استفاده می‌کند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/worker.py].

نتایج را به‌صورت Asynchronous در پایگاه داده PostgreSQL ذخیره می‌کند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/worker.py].

Crawler Logic (server/crawler.py):

کراولر WikipediaCrawler از httpx برای ارسال درخواست‌های Async به API ویکی‌پدیا استفاده می‌کند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/crawler.py].

واکشی هوشمند دو مرحله‌ای:

ابتدا با API جستجو، لیستی از مقالات شامل pageid و summary را دریافت می‌کند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/crawler.py].

سپس با استفاده از pageid های به‌دست آمده، در یک درخواست گروهی، جزئیات کامل (شامل full_text و url) را واکشی می‌کند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/crawler.py].

DataSaverAsync مسئول ذخیره‌سازی داده‌ها در دیتابیس با استفاده از SQLAlchemy و جلوگیری از درج تکراری است [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/crawler.py].

Tkinter Client (client/main.py):

یک رابط کاربری گرافیکی (GUI) دسکتاپ برای تعامل با سیستم [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/client/main.py].

ارسال درخواست Async: با کلیک روی دکمه "جستجو (Async)"، یک درخواست POST با استفاده از requests به سرور FastAPI ارسال کرده و سپس وضعیت آن را رصد می‌کند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/client/main.py].

بارگیری Sync: با کلیک روی "بارگیری از پایگاه داده (Sync)"، مستقیماً به PostgreSQL متصل شده و نتایج را نمایش می‌دهد [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/client/main.py].

نمایش نتایج در یک جدول Treeview و نمایش جزئیات کامل مقاله (متن، URL و...) در یک ScrolledText با کلیک بر روی هر مورد [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/client/main.py].

Database Layer (shared/database.py):

پیکربندی اتصال به پایگاه داده PostgreSQL با استفاده از SQLAlchemy [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/shared/database.py].

تعریف هر دو موتور اتصال Async (برای FastAPI/ARQ) و Sync (برای کلاینت Tkinter) [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/shared/database.py].

تعریف مدل WikipediaArticle که از pageid به عنوان کلید یونیک برای جلوگیری از تکرار استفاده می‌کند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/shared/database.py].

بارگیری DATABASE_URL از فایل .env [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/shared/database.py].

Redis:

به‌عنوان Message Broker اصلی برای سیستم صف ARQ عمل می‌کند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/worker.py].

همچنین توسط fastapi-limiter برای ردیابی محدودیت درخواست‌ها استفاده می‌شود [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/server.py].

✨ ویژگی‌های کلیدی

پردازش کاملاً Asynchronous: استفاده کامل از asyncio در FastAPI، ARQ، و HTTPLX برای حداکثر کارایی در عملیات I/O.

اجرای پس‌زمینه: جستجوهای زمان‌بر ویکی‌پدیا در ورکر arq و خارج از چرخه اصلی API اجرا می‌شوند تا کلاینت منتظر نماند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/worker.py].

جلوگیری از تکرار: داده‌ها با استفاده از pageid به عنوان __unique_constraint_column__ در PostgreSQL ذخیره می‌شوند تا از ورود اطلاعات تکراری جلوگیری شود [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/shared/database.py, hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/crawler.py].

رابط کاربری تعاملی: کلاینت Tkinter به کاربر اجازه می‌دهد همزمان با اجرای جستجوهای جدید، نتایج قبلی را مرور کند [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/client/main.py].

مدیریت وابستگی مدرن: استفاده از uv برای نصب سریع و مدیریت بهینه وابستگی‌ها (بر اساس requirements.txt و uv.lock) [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/requirements.txt, hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/uv.lock].

محدودیت درخواست (Rate Limiting): API سرور در برابر درخواست‌های زیاد محافظت شده است (۲ درخواست در دقیقه) [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/server/server.py].

پشتیبانی از Python 3.13: پروژه مشخصاً برای پایتون 3.13 تنظیم شده است [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/.python-version, hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/pyproject.toml].

🛠️ پشته فناوری (Tech Stack)

زبان: Python 3.13+ [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/.python-version]

بک‌اند API: FastAPI [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/requirements.txt]

صف وظایف: ARQ [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/requirements.txt]

کلاینت GUI: Tkinter (از کتابخانه استاندارد پایتون) [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/client/main.py]

ارتباط با دیتابیس (ORM): SQLAlchemy (با درایورهای asyncpg و psycopg2-binary) [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/requirements.txt, hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/shared/database.py]

پایگاه داده: PostgreSQL

بروکر پیام / کش: Redis [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/requirements.txt]

کلاینت‌های HTTP:

httpx[http2] (در ورکر برای ارتباط Async) [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/requirements.txt]

requests (در کلاینت برای ارتباط Sync با API) [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/requirements.txt]

مدیریت محیط: python-dotenv [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/requirements.txt]

پارس کردن HTML: beautifulsoup4 [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/requirements.txt]

پکیج منیجر: uv [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/uv.lock]

🔧 راه‌اندازی و نصب (با استفاده از uv)

۱. پیش‌نیازها

Python 3.13+

یک سرور PostgreSQL در حال اجرا.

یک سرور Redis در حال اجرا (روی پورت پیش‌فرض 6379).

uv (پکیج منیجر پایتون):

# (در صورت نیاز) نصب uv اگر نصب نشده باشد:

# برای macOS / Linux
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh

# برای Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"


۲. آماده‌سازی پروژه

کلون کردن مخزن:

git clone [https://github.com/hamed-py/web_crawler.git](https://github.com/hamed-py/web_crawler.git)
cd web_crawler


ساخت فایل .env (بسیار مهم):
یک فایل .env دقیقاً در ریشه پروژه بسازید. این فایل برای اتصال به پایگاه داده PostgreSQL شما ضروری است [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/shared/database.py].

# .env
DATABASE_URL="postgresql://USERNAME:PASSWORD@localhost:5432/DATABASE_NAME"


مثال:

# .env
DATABASE_URL="postgresql://postgres:mysecretpassword@localhost:5432/crawler_db"


نکته: مطمئن شوید که پایگاه داده‌ای با نامی که وارد کرده‌اید (مثلاً crawler_db) در PostgreSQL از قبل ایجاد کرده‌اید.

ایجاد محیط مجازی و نصب وابستگی‌ها:

# ۱. ساخت محیط مجازی در پوشه .venv
uv venv

# ۲. فعال‌سازی محیط مجازی
# (در لینوکس/مک)
source .venv/bin/activate
# (در ویندوز - PowerShell)
. \.venv\Scripts\Activate.ps1
# (در ویندوز - CMD)
.\.venv\Scripts\activate

# ۳. نصب وابستگی‌ها (همگام‌سازی با فایل uv.lock)
# این دستور بهترین و سریع‌ترین راه است
uv pip sync

# (جایگزین) اگر فایل lock موجود نبود:
# uv pip install -r requirements.txt


🖥️ اجرای کامل سیستم (با سه ترمینال)

برای اجرای کامل سیستم، سه ترمینال مجزا باز کنید. در هر سه ترمینال، ابتدا محیط مجازی (.venv) را طبق دستور بالا فعال کنید.

نکته مهم: قبل از اجرا، مطمئن شوید که سرویس‌های PostgreSQL و Redis شما روشن و در حال اجرا هستند.

🏁 ترمینال ۱: اجرای ARQ Worker

ورکر arq باید همیشه در پس‌زمینه در حال اجرا باشد تا وظایف جستجو را از صف Redis دریافت و پردازش کند.

# (محیط .venv فعال است)
# اجرای arq با تنظیمات WorkerSettings از فایل server/worker.py
uv run arq server.worker.WorkerSettings


خروجی مورد انتظار: پیامی مبنی بر اتصال موفقیت‌آمیز ورکر به Redis و آماده به کار بودن.

🏁 ترمینال ۲: اجرای FastAPI Server

سرور FastAPI مسئول مدیریت API و ارسال وظایف به صف است.

# (محیط .venv فعال است)
# اجرای سرور uvicorn با قابلیت reload (مناسب برای توسعه)
uv run uvicorn server.server:app --host 127.0.0.1 --port 8000 --reload


خروجی مورد انتظار: سرور اکنون روی آدرس http://127.0.0.1:8000 در دسترس است.

🏁 ترمینال ۳: اجرای کلاینت Tkinter

کلاینت گرافیکی اجرا می‌شود. این کلاینت در اولین اجرا، جداول مورد نیاز در پایگاه داده را ایجاد خواهد کرد (به لطف تابع create_db_and_tables_sync [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/client/main.py]).

# (محیط .venv فعال است)
uv run python client/main.py


خروجی مورد انتظار: پنجره "پنل مدیریت جستجوگر ویکی‌پدیا" باز خواهد شد.

🎮 نحوه استفاده

پس از اجرای هر سه بخش (Worker، Server، Client)، به پنجره کلاینت Tkinter (پنل مدیریت) بروید [cite: hamed-py/web_crawler/web_crawler-2f6b0cb1ab055e2c4d2081be302ea86a47a2b90a/client/main.py].

در فیلد "عبارت جستجو در ویکی‌پدیا"، عبارت مورد نظر خود (مثلاً Python programming language) را تایپ کنید.

برای جستجوی جدید: روی دکمه "جستجو (Async)" کلیک کنید.

نوار وضعیت "در حال ارسال درخواست..." را نمایش می‌دهد.

درخواست شما به سرور FastAPI ارسال، در صف Redis قرار گرفته و توسط ورکر (ترمینال ۱) پردازش می‌شود.

پس از اتمام کار ورکر، پیامی مبنی بر موفقیت و تعداد نتایج جدید ذخیره شده نمایش داده می‌شود.

لیست نتایج به‌طور خودکار رفرش شده و داده‌های جدید نمایش داده می‌شوند.

برای دیدن نتایج قبلی: روی دکمه "بارگیری از پایگاه داده (Sync)" کلیک کنید.

تمام مقالات ذخیره شده در PostgreSQL مستقیماً بارگیری و در جدول نمایش داده می‌شوند.

مشاهده جزئیات: در جدول نتایج، روی هر مقاله کلیک کنید تا عنوان، PageID، URL، خلاصه و متن کامل آن در کادر سمت راست نمایش داده شود.
