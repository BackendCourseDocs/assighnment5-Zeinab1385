from fastapi import FastAPI, Query, HTTPException
import httpx
from pydantic import BaseModel, Field
from typing import List, Optional
import math

app = FastAPI(title="Book Search Engine Professional Edition")

# --- تنظیمات و دیتابیس موقت ---
BASE_URL = "https://openlibrary.org/search.json"
my_local_books = []

# --- مدل داده (Schema) ---
class BookModel(BaseModel):
    title: str = Field(..., min_length=3, max_length=100, description="عنوان کتاب")
    author: str = Field(..., min_length=2, description="نام نویسنده")
    publisher: str = Field(default="نامشخص", description="ناشر کتاب")
    year: Optional[int] = Field(None, ge=0, description="سال انتشار")

# --- مسیر اصلی جستجو (GET) ---
@app.get("/search")
async def search_books(
    q: str = Query(..., min_length=3, max_length=100, description="کلمه کلیدی جستجو"),
    page: int = Query(1, ge=1, description="شماره صفحه"),
    size: int = Query(10, ge=1, le=50, description="تعداد نمایش در هر صفحه")
):
    combined_results = []
    search_query = q.lower()

    # ۱. جستجو در کتاب‌های محلی که خودمان اضافه کردیم
    local_matches = [
        book for book in my_local_books 
        if search_query in book["title"].lower() or search_query in book["author"].lower()
    ]
    combined_results.extend(local_matches)

    # ۲. فراخوانی API خارجی (OpenLibrary)
    async with httpx.AsyncClient() as client:
        try:
            # درخواست ۵۰ مورد اول برای داشتن دیتای کافی جهت پجینیشن
            response = await client.get(BASE_URL, params={"q": q, "limit": 50}, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            for doc in data.get("docs", []):
                external_book = {
                    "title": doc.get("title", "بدون عنوان"),
                    "author": ", ".join(doc.get("author_name", ["نامشخص"])),
                    "publisher": ", ".join(doc.get("publisher", ["نامشخص"])[:1]),
                    "year": doc.get("first_publish_year", None)
                }
                combined_results.append(external_book)
        except (httpx.HTTPError, httpx.TimeoutException):
            # اگر اینترنت قطع بود یا سایت پاسخ نداد، فقط نتایج محلی را برگردان
            pass

    # ۳. منطق پجینیشن (صفحه‌بندی)
    total_items = len(combined_results)
    total_pages = math.ceil(total_items / size)
    
    start = (page - 1) * size
    end = start + size
    paginated_data = combined_results[start:end]

    # خروجی نهایی به همراه اطلاعات صفحه (Metadata)
    return {
        "metadata": {
            "query": q,
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": size,
            "has_next": page < total_pages,
            "has_previous": page > 1
        },
        "books": paginated_data
    }

# --- مسیر اضافه کردن کتاب (POST) ---
@app.post("/add-book", status_code=201)
async def create_book(book: BookModel):
    # تبدیل مدل Pydantic به دیکشنری ساده پایتونی
    new_book_data = book.dict()
    my_local_books.append(new_book_data)
    
    return {
        "status": "success",
        "message": "کتاب با موفقیت در سیستم ثبت شد.",
        "book": new_book_data
    }

# --- اجرای پروژه ---
if __name__ == "__main__":
    import uvicorn
    # اجرای سرور روی پورت 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)