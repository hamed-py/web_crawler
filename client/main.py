import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
from typing import List, Dict, Any



script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from shared import database


class CrawlerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("پنل مدیریت جستجوگر ")
        self.geometry("900x650")


        self.articles_data_map: Dict[str, Any] = {}


        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(fill="both", expand=True)

        self.create_main_tab(self.main_frame)


        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.set_status("آماده.")

        self.server_base_url = "http://127.0.0.1:8000"

    def create_main_tab(self, frame: ttk.Frame):

        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=tk.X, pady=5)

        lbl_search = ttk.Label(input_frame, text="عبارت جستجو در ویکی‌پدیا:")
        lbl_search.pack(side=tk.LEFT, padx=(0, 5))

        self.txt_wiki_search = ttk.Entry(input_frame, width=50)
        self.txt_wiki_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.btn_crawl_wiki = ttk.Button(input_frame, text="جستجو (Async)",
                                         command=self.start_wiki_job_thread)
        self.btn_crawl_wiki.pack(side=tk.LEFT, padx=5)

        self.btn_load_wiki = ttk.Button(input_frame, text="بارگیری از پایگاه داده (Sync)",
                                        command=self.load_articles_from_db)
        self.btn_load_wiki.pack(side=tk.LEFT, padx=5)


        paned_window = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, pady=10)


        tree_frame = ttk.Frame(paned_window)
        paned_window.add(tree_frame, weight=1)


        self.tree = ttk.Treeview(tree_frame, columns=("title", "summary"), show="headings")
        self.tree.heading("title", text="عنوان مقاله")
        self.tree.heading("summary", text="خلاصه")

        # تنظیم عرض ستون‌ها
        self.tree.column("title", width=200, minwidth=150)
        self.tree.column("summary", width=300, minwidth=200)

        # افزودن اسکرول‌بار به جدول
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # [جدید] اتصال رویداد کلیک (انتخاب) به تابع
        self.tree.bind("<<TreeviewSelect>>", self.on_article_select)

        # --- پنل سمت راست (نمایش جزئیات) ---
        details_frame = ttk.Frame(paned_window)
        paned_window.add(details_frame, weight=2)

        lbl_details = ttk.Label(details_frame, text="متن کامل و جزئیات مقاله:")
        lbl_details.pack(anchor=tk.W, pady=(0, 5))

        self.txt_details = scrolledtext.ScrolledText(details_frame, wrap=tk.WORD, height=25, width=60)
        self.txt_details.pack(fill=tk.BOTH, expand=True)
        self.txt_details.configure(state='disabled')

    def on_article_select(self, event=None):

        try:
            selected_item_id = self.tree.selection()[0]
            article_data = self.articles_data_map.get(selected_item_id)

            if article_data:

                content = (
                    f"عنوان: {article_data.title}\n"
                    f"PageID: {article_data.pageid}\n"
                    f"URL: {article_data.url}\n"
                    f"{'-' * 40}\n\n"
                    f"خلاصه:\n{article_data.summary}\n"
                    f"{'-' * 40}\n\n"
                    f"متن کامل مقاله:\n{article_data.full_text or 'متن کامل واکشی نشده است.'}"
                )
                self.display_details_text(content)
        except IndexError:
            pass  # اگر کلیک خالی بود یا جدول پاک شد
        except Exception as e:
            print(f"Error in on_article_select: {e}")

    def set_status(self, message):

        self.after(0, self.status_var.set, message)

    def display_articles_in_tree(self, articles: List[Any]):

        def _display():

            self.tree.delete(*self.tree.get_children())
            self.articles_data_map.clear()


            for article in articles:
                values = (article.title, article.summary)

                item_id = self.tree.insert("", tk.END, values=values)

                self.articles_data_map[item_id] = article

        self.after(0, _display)

    def display_details_text(self, content: str):

        def _display():
            self.txt_details.configure(state='normal')
            self.txt_details.delete('1.0', tk.END)
            self.txt_details.insert(tk.END, content)
            self.txt_details.configure(state='disabled')

        self.after(0, _display)

    def set_buttons_state(self, state: str):
        """[اصلاح] فعال/غیرفعال کردن دکمه‌ها (حذف دکمه‌های Quotes)."""

        def _set_state():
            self.btn_crawl_wiki.config(state=state)

        self.after(0, _set_state)

    def load_articles_from_db(self):

        self.set_status("در حال بارگیری مقالات از پایگاه داده...")
        try:
            with database.SyncSessionLocal() as db:
                articles = db.query(database.WikipediaArticle).order_by(database.WikipediaArticle.id.desc()).all()

            # نمایش داده‌ها در جدول
            self.display_articles_in_tree(articles)
            # پاک کردن پنجره جزئیات
            self.display_details_text("")

            self.set_status(f"{len(articles)} مقاله از پایگاه داده بارگیری شد.")
        except Exception as e:
            messagebox.showerror("خطای پایگاه داده", f"خطا در اتصال Sync به DB:\n{e}")
            self.set_status("خطا در بارگیری.")

    # --- بخش مدیریت Job (ارتباط Async با سرور FastAPI) ---

    def start_wiki_job_thread(self):

        search_term = self.txt_wiki_search.get()
        if not search_term:
            messagebox.showwarning("خطای ورودی", "لطفاً یک عبارت برای جستجو وارد کنید.")
            return

        task_details = {
            "crawler_name": "wikipedia",
            "params": {"search_term": search_term}
        }
        self.start_job_thread(task_details)

    def start_job_thread(self, task_details: dict):

        crawler_name = task_details.get("crawler_name", "unknown")
        self.set_status(f"در حال ارسال درخواست '{crawler_name}' به سرور...")
        self.set_buttons_state(tk.DISABLED)

        job_thread = threading.Thread(
            target=self.run_job_lifecycle,
            args=(task_details,),
            daemon=True
        )
        job_thread.start()

    def run_job_lifecycle(self, task_details: dict):

        try:
            job_id = self.submit_job(task_details)
            if not job_id:
                return

            self.set_status(f"درخواست با ID: {job_id} ارسال شد. در حال رصد وضعیت...")

            start_time = time.time()
            while time.time() - start_time < 300:  # 5 دقیقه مهلت
                status, result = self.check_job_status(job_id)

                if status == "complete":
                    self.set_status(f"درخواست {job_id} با موفقیت تمام شد.")
                    self.handle_job_success(result)
                    return

                elif status == "failed":
                    self.set_status(f"درخواست {job_id} شکست خورد.")
                    self.handle_job_failure(result)
                    return

                self.set_status(f"درخواست {job_id} در حال اجرا... (وضعیت: {status})")
                time.sleep(3)

            self.set_status(f"درخواست {job_id} زمان‌بر شد (Timeout).")
            self.after(0, messagebox.showwarning, "پایان مهلت", "پاسخی از سرور دریافت نشد.")

        except Exception as e:
            self.set_status(f"خطا در مدیریت درخواست: {e}")
            self.after(0, messagebox.showerror, "خطای کلاینت", f"خطای پیش‌بینی‌نشده در کلاینت:\n{e}")
        finally:
            self.set_buttons_state(tk.NORMAL)

    def submit_job(self, task_details: dict) -> str | None:

        try:
            response = requests.post(
                f"{self.server_base_url}/jobs/crawl",
                json=task_details,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("job_id")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                self.after(0, messagebox.showerror, "خطای Rate Limit",
                           "شما بیش از حد مجاز (2 بار در دقیقه) درخواست دادید. لطفا صبر کنید.")
            else:
                self.after(0, messagebox.showerror, "خطای API", f"خطا در ارسال درخواست:\n{e.response.text}")

        except requests.RequestException as e:
            self.after(0, messagebox.showerror, "خطای اتصال",
                       f"خطا در اتصال به سرور:\n{e}\nآیا سرور FastAPI (server.py) در حال اجراست؟")

        return None

    def check_job_status(self, job_id: str) -> (str, dict):

        response = requests.get(f"{self.server_base_url}/jobs/status/{job_id}", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("status"), data.get("result")

    def handle_job_success(self, result: dict):

        found = result.get('found', 0)
        saved = result.get('saved', 0)
        message = f"جستجو با موفقیت انجام شد.\n\nموارد یافت شده: {found}\nموارد جدید ذخیره شده: {saved}\n\nدر حال بارگیری خودکار نتایج جدید از پایگاه داده..."
        self.after(0, messagebox.showinfo, "درخواست موفق", message)


        self.after(0, self.load_articles_from_db)

    def handle_job_failure(self, result: dict):

        error = result.get('error', 'خطای ناشناخته در سرور.')
        message = f"فرآیند جستجو در سرور با خطا مواجه شد:\n\n{error}"
        self.after(0, messagebox.showerror, "درخواست ناموفق", message)


if __name__ == "__main__":
    print("Starting client (v5.0 - Wikipedia Only)...")
    print("بررسی و ساخت جداول (Sync method)...")
    try:

        database.create_db_and_tables_sync()

        app = CrawlerApp()
        app.mainloop()

    except Exception as e:
        print(f"خطای بحرانی: امکان اتصال به پایگاه داده PostgreSQL وجود ندارد.")
        print(f"Error: {e}")
        print("لطفا از روشن بودن سرویس PostgreSQL و صحت اطلاعات .env اطمینان حاصل کنید.")