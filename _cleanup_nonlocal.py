"""
Veritabanındaki Kocaeli referansı olmayan koordinatsız haberleri siler.
Calistir: .venv\Scripts\python.exe _cleanup_nonlocal.py

Silme yapılmadan önce hangi haberlerin etkileneceğini görmek için:
  .venv\Scripts\python.exe _cleanup_nonlocal.py --dry-run
"""
import asyncio, sys, os, re, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true', help='Silmeden sadece listele')
args = parser.parse_args()

DISTRICTS = [
    "Başiskele", "Çayırova", "Darıca", "Derince", "Dilovası",
    "Gebze", "Gölcük", "İzmit", "Kandıra", "Karamürsel",
    "Kartepe", "Körfez"
]


def is_kocaeli_related(text: str) -> bool:
    if re.search(r'(?<![a-zA-ZçğışöüÇĞİÖŞÜ])kocaeli', text, re.IGNORECASE):
        return True
    for d in DISTRICTS:
        if re.search(rf'(?<![a-zA-ZçğışöüÇĞİÖŞÜ]){re.escape(d)}', text, re.IGNORECASE):
            return True
    return False


async def main():
    from src.utils.database import db
    await db.connect_db()
    database = db.get_db()

    all_articles = await database.news.find({}).to_list(length=None)
    to_delete = []

    for a in all_articles:
        loc = a.get('location') or {}
        if loc.get('coordinates'):
            continue  # Zaten haritada, dokunma

        title = a.get('title', '')
        content = a.get('cleaned_content') or a.get('content') or ''
        full_text = f"{title} {content}"

        if not is_kocaeli_related(full_text):
            to_delete.append(a)

    print(f"Silinecek haber sayısı: {len(to_delete)}")
    for a in to_delete:
        print(f"  [{a.get('news_type')}] {a.get('title', '')[:70]}")

    if not args.dry_run and to_delete:
        ids = [a['_id'] for a in to_delete]
        result = await database.news.delete_many({'_id': {'$in': ids}})
        print(f"\nSilindi: {result.deleted_count} haber")
    elif args.dry_run:
        print("\n(Dry-run: gerçek silme yapılmadı)")

    await db.close_db()


asyncio.run(main())
