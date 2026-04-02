import sys, asyncio
sys.path.insert(0, 'backend')
import os; os.chdir('backend')
from src.utils.database import db
from src.config import NEWS_TYPES

async def run():
    await db.connect_db()
    database = db.get_db()
    art = await database.news.find_one({'title': {'$regex': 'LPG', '$options': 'i'}})
    if not art:
        print("Article not found")
        return
    title = art.get('title', '')
    content = art.get('content', '') + ' ' + art.get('cleaned_content', '')
    full = (title + ' ' + content).lower()
    print(f"news_type: {art.get('news_type')}")
    print(f"Title: {title[:80]}")
    for cat, keywords in NEWS_TYPES.items():
        matches = [kw for kw in keywords if kw.lower() in full]
        if matches:
            print(f"{cat}: {matches}")
    await db.close_db()

asyncio.run(run())
