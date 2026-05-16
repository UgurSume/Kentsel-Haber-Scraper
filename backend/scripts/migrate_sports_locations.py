"""One-off migration for sports news location consistency.

Rules:
- If a sports article has a specific location text but no coordinates, geocode it.
- If a sports article has no location (or only generic "Kocaeli"), fallback to stadium.
- If a Kocaelispor article has generic city location, force stadium fallback.
"""

import asyncio
import re
from datetime import datetime

from src.config import KOCAELISPOR_STADIUM
from src.services.geocoding_service import geocoding_service
from src.utils.database import db


def _is_generic_city_location(value: str) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    return normalized in {"kocaeli", "kocaeli, turkey", "kocaeli, turkiye"}


async def run() -> None:
    await db.connect_db()
    collection = db.get_db().news

    cursor = collection.find({"news_type": "Spor"})

    total = 0
    updated = 0
    fallback_to_stadium = 0
    geocoded_specific = 0
    unchanged = 0

    async for article in cursor:
        total += 1

        title = (article.get("title") or "")
        is_kocaelispor = bool(re.search(r"kocaeli\s*spor", title, re.IGNORECASE))

        location = article.get("location") or {}
        location_text = (location.get("text") or "").strip()
        coordinates = location.get("coordinates")
        district = location.get("district")

        next_location = dict(location)
        changed = False

        should_force_stadium = False
        if is_kocaelispor:
            should_force_stadium = True
        elif (not is_kocaelispor) and (not coordinates):
            if not location_text or _is_generic_city_location(location_text):
                should_force_stadium = True

        if should_force_stadium:
            next_location["text"] = KOCAELISPOR_STADIUM["name"]
            next_location["coordinates"] = {
                "lat": KOCAELISPOR_STADIUM["lat"],
                "lng": KOCAELISPOR_STADIUM["lng"],
            }
            next_location["district"] = KOCAELISPOR_STADIUM["district"]
            fallback_to_stadium += 1
            changed = True
        else:
            # Keep article's own location if it exists; only backfill missing coordinates.
            if location_text and not coordinates and not _is_generic_city_location(location_text):
                geocoded = geocoding_service.geocode_location(location_text)
                if geocoded:
                    next_location["coordinates"] = geocoded
                    geocoded_specific += 1
                    changed = True

            if not district and next_location.get("text") == KOCAELISPOR_STADIUM["name"]:
                next_location["district"] = KOCAELISPOR_STADIUM["district"]
                changed = True

        if changed:
            await collection.update_one(
                {"_id": article["_id"]},
                {
                    "$set": {
                        "location": next_location,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            updated += 1
        else:
            unchanged += 1

    await db.close_db()

    print("[MIGRATION] Sports location migration completed")
    print(f"[MIGRATION] total_sports={total}")
    print(f"[MIGRATION] updated={updated}")
    print(f"[MIGRATION] fallback_to_stadium={fallback_to_stadium}")
    print(f"[MIGRATION] geocoded_specific={geocoded_specific}")
    print(f"[MIGRATION] unchanged={unchanged}")


if __name__ == "__main__":
    asyncio.run(run())
