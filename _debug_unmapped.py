"""
Haritaya eklenemeyen haberleri inceler.
Calistir: .venv\Scripts\python.exe _debug_unmapped.py
"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))


async def main():
    from src.utils.database import db
    await db.connect_db()
    database = db.get_db()

    # Koordinatı olmayan haberler
    all_articles = await database.news.find({}).to_list(length=None)
    no_coord = [
        a for a in all_articles
        if not (a.get('location') or {}).get('coordinates')
    ]

    total = len(all_articles)
    unmapped = len(no_coord)
    print(f"Toplam haber: {total}, Koordinatsiz: {unmapped}")
    print("=" * 70)

    for a in no_coord:
        loc = a.get('location') or {}
        print(f"[{a.get('news_type')}] {a.get('title', '')[:70]}")
        print(f"  location.text    : {loc.get('text')}")
        print(f"  location.district: {loc.get('district')}")
        # İlk 200 karakter içerik
        cleaned = a.get('cleaned_content') or a.get('content') or ''
        print(f"  içerik (ilk 200) : {cleaned[:200]}")
        print()

    await db.close_db()


asyncio.run(main())
