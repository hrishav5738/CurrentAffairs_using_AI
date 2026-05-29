from newspaper import Article

from app.fetchers.rss_fetchers import fetch_news


def extract_article(url):

    try:

        article = Article(url)

        article.download()

        article.parse()

        return {
            "title": article.title,
            "text": article.text,
            "authors": article.authors,
            "publish_date": str(article.publish_date)
        }

    except Exception as e:

        print(f"Error extracting article: {e}")

        return None


def process_articles():

    news_list = fetch_news()

    extracted_articles = []

    for news in news_list:

        print(f"\nExtracting: {news['title']}")

        # article_data = extract_article(news["link"])
        article_data = extract_article(news["link"])

        if article_data:

            article_data["source"] = news["source"]

            article_data["link"] = news["link"]

        if article_data:

            extracted_articles.append(article_data)

            print("✅ Extraction Successful")

        else:

            print("❌ Extraction Failed")

    return extracted_articles


if __name__ == "__main__":

    articles = process_articles()

    print(f"\nTotal Extracted Articles: {len(articles)}")