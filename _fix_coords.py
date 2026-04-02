"""
Fixes broken GeoJSON-format location objects back to proper {text, coordinates:{lat,lng}, district} format.
Run from repo root: .venv\Scripts\python.exe _fix_coords.py
"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

async def main():
    from src.utils.database import db
    await db.connect_db()
    database = db.get_db()

    articles = await database.news.find({}).to_list(length=None)
    fixed = skipped = 0

    for art in articles:
        loc = art.get('location') or {}

        # Detect GeoJSON format: {"type": "Point", "coordinates": [lng, lat]}
        if loc.get('type') == 'Point' and isinstance(loc.get('coordinates'), list):
            coords_arr = loc['coordinates']
            lng, lat = coords_arr[0], coords_arr[1]

            # Recover text and district from top-level fields set by _reclassify.py
            text = art.get('location_text') or art.get('location', {}).get('text')
            district = art.get('district') or art.get('location', {}).get('district')

            new_location = {
                'text': text,
                'coordinates': {'lat': lat, 'lng': lng},
                'district': district,
            }

            await database.news.update_one(
                {'_id': art['_id']},
                {'$set': {'location': new_location}}
            )
            fixed += 1
        else:
            skipped += 1

    await db.close_db()
    print(f"Fixed: {fixed}, already OK: {skipped}")

asyncio.run(main())
