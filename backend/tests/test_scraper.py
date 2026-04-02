"""
Test Çağdaş Kocaeli scraper
"""
import sys
import asyncio

# Add parent directory to path
sys.path.insert(0, '..')

from src.scrapers import CagdasKocaeliScraper


async def test_scraper():
    """Test the Çağdaş Kocaeli scraper"""
    print("🧪 Testing Çağdaş Kocaeli Scraper...\n")

    scraper = CagdasKocaeliScraper()

    print(f"📰 Source: {scraper.source_name}")
    print(f"🌐 Base URL: {scraper.base_url}\n")

    print("🔍 Starting scraping process (last 3 days)...\n")

    try:
        articles = scraper.scrape(days=3)

        print(f"\n📊 Results:")
        print(f"   Total articles found: {len(articles)}\n")

        if articles:
            print("📰 Sample Articles:\n")
            for i, article in enumerate(articles[:3], 1):
                print(f"{i}. {'-' * 60}")
                print(f"   Title: {article['title'][:80]}...")
                print(f"   Date: {article['publish_date']}")
                print(f"   Content: {article['content'][:100]}...")
                print(f"   URL: {article['url']}")
                print()

        else:
            print("⚠️  No articles found. This could mean:")
            print("   - The website structure has changed")
            print("   - Network connection issues")
            print("   - No recent articles in the last 3 days")

        print("✅ Scraper test completed!")
        return True

    except Exception as e:
        print(f"❌ Error testing scraper: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_scraper())
    sys.exit(0 if result else 1)
