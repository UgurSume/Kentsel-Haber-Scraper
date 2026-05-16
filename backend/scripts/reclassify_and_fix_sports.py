"""Reclassify existing news and fix sports locations based on current rules.

Run:
  Set-Location backend
  $env:PYTHONPATH='.'
    ../.venv/Scripts/python.exe scripts/reclassify_and_fix_sports.py
"""

import asyncio
import re
from datetime import datetime

from src.config import KOCAELISPOR_STADIUM, IZMIT_FALLBACK_CENTER
from src.services.geocoding_service import geocoding_service
from src.services.nlp_service import nlp_service
from src.utils.database import db


def _is_generic_city_location(value: str) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    return normalized in {"kocaeli", "kocaeli, turkey", "kocaeli, turkiye"}


async def run() -> None:
    await db.connect_db()
    collection = db.get_db().news

    total = 0
    changed_type = 0
    changed_location = 0
    unchanged = 0

    cursor = collection.find({})
    async for article in cursor:
        total += 1
        title = article.get("title") or ""
        content = article.get("content") or ""
        cleaned_content = article.get("cleaned_content") or content
        full_text = f"{title} {cleaned_content}"

        new_type, new_keywords = nlp_service.classify_news(title, cleaned_content)

        location = article.get("location") or {}
        location_text = (location.get("text") or "").strip()
        coords = location.get("coordinates")
        district = location.get("district")

        extracted_location = nlp_service.extract_location(full_text)

        next_location = dict(location)

        if new_type == "Spor":
            # Spor haberleri stadyum merkezine sabitlenir.
            next_location = {
                "text": KOCAELISPOR_STADIUM["name"],
                "coordinates": {
                    "lat": KOCAELISPOR_STADIUM["lat"],
                    "lng": KOCAELISPOR_STADIUM["lng"],
                },
                "district": KOCAELISPOR_STADIUM["district"],
            }
        else:
            # Spor dışı haberde konum belirsizse/generikse İzmit merkeze taşı.
            chosen_loc = extracted_location or location_text
            if not chosen_loc or _is_generic_city_location(chosen_loc):
                next_location = {
                    "text": IZMIT_FALLBACK_CENTER["name"],
                    "coordinates": {
                        "lat": IZMIT_FALLBACK_CENTER["lat"],
                        "lng": IZMIT_FALLBACK_CENTER["lng"],
                    },
                    "district": IZMIT_FALLBACK_CENTER["district"],
                }
            else:
                geocoded = geocoding_service.geocode_location(chosen_loc)
                if geocoded:
                    next_location = {
                        "text": chosen_loc,
                        "coordinates": {
                            "lat": geocoded["lat"],
                            "lng": geocoded["lng"],
                        },
                        "district": district,
                    }
                else:
                    next_location = {
                        "text": IZMIT_FALLBACK_CENTER["name"],
                        "coordinates": {
                            "lat": IZMIT_FALLBACK_CENTER["lat"],
                            "lng": IZMIT_FALLBACK_CENTER["lng"],
                        },
                        "district": IZMIT_FALLBACK_CENTER["district"],
                    }

        update = {}
        if new_type != article.get("news_type"):
            update["news_type"] = new_type
            changed_type += 1
        if next_location != location:
            update["location"] = next_location
            changed_location += 1
        if new_keywords != article.get("keywords"):
            update["keywords"] = new_keywords

        if update:
            update["updated_at"] = datetime.utcnow()
            await collection.update_one({"_id": article["_id"]}, {"$set": update})
        else:
            unchanged += 1

    await db.close_db()

    print("[RECLASSIFY] Completed")
    print(f"[RECLASSIFY] total={total}")
    print(f"[RECLASSIFY] changed_type={changed_type}")
    print(f"[RECLASSIFY] changed_location={changed_location}")
    print(f"[RECLASSIFY] unchanged={unchanged}")


if __name__ == "__main__":
    asyncio.run(run())
