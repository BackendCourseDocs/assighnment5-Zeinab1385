from fastapi import FastAPI, Query, HTTPException, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import BaseModel, Field
from typing import List, Optional
import math
import shutil
import os
import uuid # برای تولید نام‌های غیرتکراری برای فایل‌ها

app = FastAPI(
    title="Book Search Engine Pro",
    description="سیستم مدیریت کتاب با قابلیت آپلود مستقیم و جستجوی هوشمند",
    version="2.0.0"
)

# --- تنظیمات زیرساختی ---
UPLOAD_DIR = "static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

BASE_URL = "https://openlibrary.org/search.json"
my_local_books = []

# --- مسیر ۱: اضافه کردن کتاب و آپلود عکس (همه در یک فرم) ---
@app.post("/add-book", tags=["مدیریت کتاب"])
async def create_book_integrated(
    title: str = Form(..., min_length=3, description="نام کتاب را اینجا بنویسید"),
    author: str = Form(..., min_length=2, description="نام نویسنده"),
    publisher: str = Form("نامشخص"),
    year: Optional[int] = Form(None),
    file: UploadFile = File(..., description="فایل عکس کاور کتاب را انتخاب کنید")
):
    # الف) جلوگیری از تکراری شدن نام فایل با استفاده از uuid
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # ب) ذخیره فیزیکی فایل روی هارد
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # ج) ساخت آبجکت کتاب و ذخیره در لیست (دی‌تا‌بیس موقت)
    image_url = f"http://127.0.0.1:8000/static/images/{unique_filename}"
    new_book = {
        "title": title,
        "author": author,
        "publisher": publisher,
        "year": year,
        "image": image_url
    }
    my_local_books.append(new_book)
    
    return {"status": "موفقیت‌آمیز", "data": new_book}

# --- مسیر ۲: جستجوی هوشمند (محلی + آنلاین) ---
@app.get("/search", tags=["جستجو"])
async def search_books(
    q: str = Query(..., min_length=3, description="کلمه کلیدی برای جستجو"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50)
):
    combined_results = []
    search_query = q.lower()

    # ۱. جستجو در دیتای خودمان (کتاب‌های آپلود شده)
    for book in my_local_books:
        if search_query in book["title"].lower() or search_query in book["author"].lower():
            combined_results.append(book)

    # ۲. جستجو در دیتای جهانی (OpenLibrary)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(BASE_URL, params={"q": q, "limit": 30})
            response.raise_for_status()
            data = response.json()
            
            for doc in data.get("docs", []):
                cover_id = doc.get("cover_i")
                combined_results.append({
                    "title": doc.get("title"),
                    "author": ", ".join(doc.get("author_name", ["نامشخص"])),
                    "publisher": ", ".join(doc.get("publisher", ["نامشخص"])[:1]),
                    "year": doc.get("first_publish_year"),
                    "image": f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
                })
        except:
            pass # اگر اینترنت قطع بود، فقط دیتای محلی را برمی‌گرداند

    # ۳. پیاده‌سازی صفحه‌بندی (Pagination)
    start = (page - 1) * size
    end = start + size
    
    return {
        "metadata": {
            "total_results": len(combined_results),
            "page": page,
            "size": size,
            "total_pages": math.ceil(len(combined_results) / size)
        },
        "books": combined_results[start:end]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)