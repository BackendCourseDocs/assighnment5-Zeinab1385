from fastapi import FastAPI, Query, HTTPException
import httpx

app = FastAPI(title="Book Search Engine")

BASE_URL = "https://openlibrary.org/search.json"

@app.get("/search")
async def search_books(q: str = Query(..., description="کلمه کلیدی برای جستجو")):
    async with httpx.AsyncClient() as client:
        try:
            # فراخوانی API اصلی با لیمیت درخواستی شما
            response = await client.get(BASE_URL, params={"q": q, "limit": 58})
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            raise HTTPException(status_code=503, detail="خطا در ارتباط با سرویس OpenLibrary")

    results = []
    search_query = q.lower()

    for doc in data.get("docs", []):
        title = doc.get("title", "")
        # تبدیل لیست نویسندگان و ناشران به رشته برای جستجو
        authors = ", ".join(doc.get("author_name", []))
        publishers = ", ".join(doc.get("publisher", []))

        # فیلتر کردن بر اساس شرط شما (عنوان، نویسنده یا ناشر)
        if (search_query in title.lower() or 
            search_query in authors.lower() or 
            search_query in publishers.lower()):
            
            results.append({
                "title": title,
                "author": authors,
                "publisher": publishers,
                "year": doc.get("first_publish_year", "نامشخص")
            })

    return {
        "query": q,
        "total_found": len(results),
        "books": results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)