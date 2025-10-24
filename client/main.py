import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import requests
import time
import json
from shared import database

class CrawlerApp(tk.Tk):
   
    def __init__(self):
        super().__init__()
        self.title("Crawler Control Panel (v3.0 - Job Queue Client)")
        self.geometry("800x600")
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)
        self.quote_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.quote_frame, text="Quotes Crawler")
        self.create_quote_tab(self.quote_frame)

        self.divar_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.divar_frame, text="Divar Crawler (Laptop/Tehran)")
        self.create_divar_tab(self.divar_frame)

        # نوار وضعیت
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.set_status("آماده.")
        
        # URL سرور
        self.server_base_url = "http://127.0.0.1:8000"

    def create_tab_widgets(self, parent_frame, load_cmd, crawl_cmd):
        top_frame = ttk.Frame(parent_frame)
        top_frame.pack(fill=tk.X, pady=5)

        btn_load = ttk.Button(top_frame, text="بارگیری مستقیم از دیتابیس (Sync)", command=load_cmd)
        btn_load.pack(side=tk.LEFT, padx=5)

        btn_crawl = ttk.Button(top_frame, text="ارسال Job کراول به سرور (Async)", command=crawl_cmd)
        btn_crawl.pack(side=tk.LEFT, padx=5)

        txt_display = scrolledtext.ScrolledText(parent_frame, wrap=tk.WORD, height=25, width=90)
        txt_display.pack(fill=tk.BOTH, expand=True, pady=5)
        txt_display.configure(state='disabled')
        
        return btn_load, btn_crawl, txt_display

    def create_quote_tab(self, frame):
        self.btn_load_quotes, self.btn_crawl_quotes, self.txt_quotes = self.create_tab_widgets(
            frame,
            self.load_quotes_from_db,
            lambda: self.start_job_thread("quotes")
        )

    def create_divar_tab(self, frame):
        self.btn_load_divar, self.btn_crawl_divar, self.txt_divar = self.create_tab_widgets(
            frame,
            self.load_listings_from_db,
            lambda: self.start_job_thread("divar_laptops")
        )

    def set_status(self, message):
        """آپدیت نوار وضعیت (امن برای Thread)."""
        self.after(0, self.status_var.set, message)

    def display_data(self, text_widget, content: str):
        """نمایش داده در ویجت متنی (امن برای Thread)."""
        def _display():
            text_widget.configure(state='normal')
            text_widget.delete('1.0', tk.END)
            text_widget.insert(tk.END, content)
            text_widget.configure(state='disabled')
        self.after(0, _display)

    def set_buttons_state(self, state: str):
        """فعال/غیرفعال کردن دکمه‌ها (امن برای Thread)."""
        def _set_state():
            self.btn_crawl_quotes.config(state=state)
            self.btn_crawl_divar.config(state=state)
        self.after(0, _set_state)

    # --- توابع مستقل خواندن از دیتابیس (Sync) ---
    # این توابع بدون تغییر هستند و "مستقل" کار می‌کنند
    def load_quotes_from_db(self):
        self.set_status("در حال بارگیری نقل‌قول‌ها از DB...")
        try:
            with database.SyncSessionLocal() as db:
                quotes = db.query(database.Quote).order_by(database.Quote.id.desc()).all()
            output = f"--- {len(quotes)} نقل قول از دیتابیس (Sync) بارگیری شد ---\n\n"
            for q in quotes: output += f'"{q.text}"\n- {q.author}\n' + "-" * 30 + "\n"
            self.display_data(self.txt_quotes, output)
            self.set_status(f"{len(quotes)} نقل قول بارگیری شد.")
        except Exception as e:
            messagebox.showerror("خطای دیتابیس", f"خطا در اتصال Sync به DB:\n{e}\nآیا سرور Postgres روشن است؟")
            self.set_status("خطا در بارگیری.")

    def load_listings_from_db(self):
        self.set_status("در حال بارگیری آگهی‌های دیوار از DB...")
        try:
            with database.SyncSessionLocal() as db:
                listings = db.query(database.DivarListing).order_by(database.DivarListing.id.desc()).all()
            output = f"--- {len(listings)} آگهی دیوار از دیتابیس (Sync) بارگیری شد ---\n\n"
            for item in listings: output += f'عنوان: {item.title}\nقیمت: {item.price}\nلینک: {item.url}\n' + "-" * 30 + "\n"
            self.display_data(self.txt_divar, output)
            self.set_status(f"{len(listings)} آگهی بارگیری شد.")
        except Exception as e:
            messagebox.showerror("خطای دیتابیس", f"خطا در اتصال Sync به DB:\n{e}\nآیا سرور Postgres روشن است؟")
            self.set_status("خطا در بارگیری.")

    # --- بخش مدیریت Job (کاملاً جدید و هوشمند) ---

    def start_job_thread(self, crawler_name: str):
        """کراولر را در یک نخ (Thread) جداگانه اجرا می‌کند."""
        self.set_status(f"در حال ارسال Job برای '{crawler_name}' به سرور...")
        self.set_buttons_state(tk.DISABLED) # غیرفعال کردن دکمه‌ها

        # ایجاد و اجرای نخ
        job_thread = threading.Thread(
            target=self.run_job_lifecycle,
            args=(crawler_name,),
            daemon=True
        )
        job_thread.start()

    def run_job_lifecycle(self, crawler_name: str):
        """
        کل چرخه حیات Job: 1. ارسال 2. رصد 3. نتیجه
        """
        try:
            # 1. ارسال Job
            job_id = self.submit_job(crawler_name)
            if not job_id:
                return # خطا قبلا نمایش داده شده

            self.set_status(f"Job با ID: {job_id} ارسال شد. در حال رصد وضعیت...")

            # 2. رصد (Polling)
            start_time = time.time()
            while time.time() - start_time < 300: # 5 دقیقه مهلت
                status, result = self.check_job_status(job_id)
                
                if status == "complete":
                    self.set_status(f"Job {job_id} با موفقیت تمام شد.")
                    self.handle_job_success(result)
                    return # پایان موفقیت‌آمیز
                
                elif status == "failed":
                    self.set_status(f"Job {job_id} شکست خورد.")
                    self.handle_job_failure(result)
                    return # پایان ناموفق
                
                # اگر queued یا deferred یا active بود، ادامه بده
                self.set_status(f"Job {job_id} در حال اجرا... (وضعیت: {status})")
                time.sleep(3) # 3 ثانیه صبر قبل از چک کردن مجدد
            
            # اگر زمان تمام شد
            self.set_status(f"Job {job_id} زمان‌بر شد (Timeout).")
            self.after(0, messagebox.showwarning, "Timeout", "پاسخی از ورکر دریافت نشد.")

        except Exception as e:
            self.set_status(f"خطا در مدیریت Job: {e}")
            self.after(0, messagebox.showerror, "خطای کلاینت", f"خطای پیش‌بینی‌نشده در کلاینت:\n{e}")
        finally:
            self.set_buttons_state(tk.NORMAL) # فعال‌سازی مجدد دکمه‌ها

    def submit_job(self, crawler_name: str) -> str | None:
        """گام ۱: Job را به سرور ارسال می‌کند."""
        try:
            response = requests.post(
                f"{self.server_base_url}/jobs/crawl",
                json={"crawler_name": crawler_name},
                timeout=10
            )
            response.raise_for_status() # بررسی خطاهای HTTP
            data = response.json()
            return data.get("job_id")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429: # Too Many Requests
                 self.after(0, messagebox.showerror, "خطای Rate Limit", "شما بیش از حد مجاز (2 بار در دقیقه) درخواست دادید. لطفا صبر کنید.")
            else:
                 self.after(0, messagebox.showerror, "خطای API", f"خطا در ارسال Job:\n{e.response.text}")
        except requests.RequestException as e:
            self.after(0, messagebox.showerror, "خطای اتصال", f"خطا در اتصال به سرور:\n{e}\nآیا سرور FastAPI (server.py) در حال اجراست؟")
        return None

    def check_job_status(self, job_id: str) -> (str, dict):
        """گام ۲: وضعیت Job را از سرور می‌پرسد."""
        response = requests.get(f"{self.server_base_url}/jobs/status/{job_id}", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("status"), data.get("result")

    def handle_job_success(self, result: dict):
        """گام ۳: در صورت موفقیت، نتایج را نمایش می‌دهد و داده‌ها را رفرش می‌کند."""
        found = result.get('found', 0)
        saved = result.get('saved', 0)
        message = f"کراولینگ با موفقیت انجام شد.\n\nموارد یافت شده: {found}\nموارد جدید ذخیره شده: {saved}\n\nدر حال بارگیری خودکار نتایج جدید از دیتابیس..."
        self.after(0, messagebox.showinfo, "Job موفق", message)
        
        # رفرش کردن تب فعال
        current_tab_index = self.notebook.index(self.notebook.select())
        if current_tab_index == 0:
            self.after(0, self.load_quotes_from_db)
        elif current_tab_index == 1:
            self.after(0, self.load_listings_from_db)

    def handle_job_failure(self, result: dict):
        """گام ۳: در صورت شکست، خطای دریافتی از ورکر را نمایش می‌دهد."""
        error = result.get('error', 'خطای ناشناخته در ورکر.')
        message = f"فرآیند کراولینگ در سرور با خطا مواجه شد:\n\n{error}"
        self.after(0, messagebox.showerror, "Job ناموفق", message)


if __name__ == "__main__":
    print("Starting client...")
    print("Ensuring tables exist (Sync method)...")
    try:
        # کلاینت جداول را به صورت همزمان می‌سازد (اگر وجود نداشته باشند)
        database.create_db_and_tables_sync()
        app = CrawlerApp()
        app.mainloop()
    except Exception as e:
        print(f"CRITICAL ERROR: Could not connect to PostgreSQL database.")
        print("Please ensure PostgreSQL is running and .env file is correct.")