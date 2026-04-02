"""
Re-classify + re-extract location for all existing articles.
Applies the updated NLP logic (Silahlı Saldırı category + sokak-first location).
Also re-geocodes articles that gain a more specific location or whose
district was previously None.
Run from repo root with: .venv\Scripts\python.exe _reclassify.py
"""
import asyncio
import sys
import os
import re
import logging

# Make sure backend src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)


async def main():
    from src.utils.database import db
    from src.services.nlp_service import NLPService
    from src.services.geocoding_service import GeocodingService
    from src.config import KOCAELI_DISTRICTS

    nlp = NLPService()
    geo = GeocodingService()

    await db.connect_db()
    database = db.get_db()
    articles = await database.news.find({}).to_list(length=None)
    logger.info(f"Found {len(articles)} articles")

    updated = skipped = errors = 0

    for art in articles:
        try:
            title = art.get('title', '')
            content = art.get('content', '')
            full_text = f"{title} {content}"

            # Re-classify
            new_type, _ = nlp.classify_news(title, content)

            # Re-extract location
            new_location = nlp.extract_location(full_text)

            # Determine district from location string + fallback to full text
            new_district = None
            if new_location:
                for dist in KOCAELI_DISTRICTS:
                    if dist.lower() in new_location.lower():
                        new_district = dist
                        break
                if not new_district:
                    for dist in KOCAELI_DISTRICTS:
                        pattern = rf'(?<![a-zA-ZçğışöüÇĞİÖŞÜ]){re.escape(dist)}'
                        if re.search(pattern, full_text, re.IGNORECASE):
                            new_district = dist
                            break

            # Determine if re-geocoding is needed
            old_location = art.get('location', {}) or {}
            old_loc_text = art.get('location_text')
            coords_exist = bool(old_location.get('coordinates'))

            needs_geocode = (
                new_location and (
                    not coords_exist or
                    new_location != old_loc_text
                )
            )

            new_coords = None
            if needs_geocode:
                new_coords = geo.geocode_location(new_location)

            # Build update dict — only include changed fields
            update = {}

            if new_type != art.get('news_type'):
                update['news_type'] = new_type

            if new_location and new_location != old_loc_text:
                update['location_text'] = new_location

            if new_district and new_district != art.get('district'):
                update['district'] = new_district

            if new_coords:
                update['location'] = {
                    'text': new_location,
                    'coordinates': {'lat': new_coords['lat'], 'lng': new_coords['lng']},
                    'district': new_district,
                }

            if update:
                await database.news.update_one({'_id': art['_id']}, {'$set': update})
                logger.info(f"Updated [{art['_id']}] {title[:50]} — {update}")
                updated += 1
            else:
                skipped += 1

        except Exception as e:
            logger.error(f"Error on {art.get('title', '')[:40]}: {e}")
            errors += 1

    await db.close_db()
    logger.info(f"\nDone: {updated} updated, {skipped} unchanged, {errors} errors")


if __name__ == '__main__':
    asyncio.run(main())
