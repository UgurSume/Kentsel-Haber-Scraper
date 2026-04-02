"""Debug: show which keywords match each Trafik Kazası article"""
import sys, asyncio, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

async def main():
    from src.utils.database import db
    from src.config import NEWS_TYPES
    await db.connect_db()
    database = db.get_db()
    articles = await database.news.find({'news_type': 'Trafik Kazası'}).to_list(length=None)
    kws = NEWS_TYPES['Trafik Kazası']
    for art in articles:
        full = (art.get('title','') + ' ' + art.get('content','')).lower()
        hits = [kw for kw in kws if kw.lower() in full]
        print(f"\n[{art['title'][:70]}]")
        print(f"  Matches: {hits}")
    await db.close_db()

asyncio.run(main())
