import sys, asyncio, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

async def main():
    from src.utils.database import db
    from src.config import NEWS_TYPES
    await db.connect_db()
    database = db.get_db()

    kws = NEWS_TYPES.get('Trafik Kazası', [])
    print(f"Keywords ({len(kws)}):", kws)

    # Check all articles — show score for each
    articles = await database.news.find({}).to_list(length=None)
    print(f"\nAll articles scoring for Trafik Kazası:")
    for art in articles:
        content = (art.get('title', '') + ' ' + art.get('content', '')).lower()
        matches = [kw for kw in kws if kw.lower() in content]
        if matches:
            print(f"  [{art.get('news_type')}] {art['title'][:60]}")
            print(f"    -> {matches}")
    await db.close_db()

asyncio.run(main())
