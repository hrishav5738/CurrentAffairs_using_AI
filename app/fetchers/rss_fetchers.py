
import feedparser


RSS_FEEDS = {
    "The Hindu": "https://www.thehindu.com/news/national/feeder/default.rss",
    "Indian Express": "https://indianexpress.com/section/india/feed/",
}


IMPORTANT_KEYWORDS = [
    "RBI", "ISRO", "NASA", "Supreme Court", "Government",
    "Election", "Parliament", "India", "UN", "WHO",
    "Economy", "Environment", "Science", "Technology",
    "Sports", "Olympics", "Cricket", "Policy", "Scheme",
    "Defence", "Military", "Bank", "Education", "Health",
    "Climate Change", "International Relations"
]


MAX_HEADLINES = 50


def fetch_news():

    unique_news = set()

    filtered_news = []

    for source, url in RSS_FEEDS.items():

        print(f"\n===== {source} =====\n")

        feed = feedparser.parse(url)

        for entry in feed.entries:

            title = entry.title.strip()

            if any(keyword.lower() in title.lower()
                   for keyword in IMPORTANT_KEYWORDS):

                if title.lower() not in unique_news:

                    unique_news.add(title.lower())

                    news_item = {
                        "source": source,
                        "title": title,
                        "link": entry.link
                    }

                    filtered_news.append(news_item)

                    print(f"📰 {title}")
                    print(f"🔗 {entry.link}")
                    print("-" * 100)

                    if len(filtered_news) >= MAX_HEADLINES:
                        return filtered_news

    return filtered_news


if __name__ == "__main__":

    news = fetch_news()

    print(f"\n✅ Total headlines collected: {len(news)}")