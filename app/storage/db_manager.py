import sqlite3
import os
from datetime import datetime

# Resolve absolute path to project root database file
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DB_PATH = os.path.join(DB_DIR, "current_affairs.db")


def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionary-like objects
    return conn


def init_db():
    """Initializes SQLite database tables if they do not exist yet."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table to store UPSC articles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            source TEXT,
            link TEXT,
            publish_date TEXT,
            summary TEXT,
            category TEXT,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table to store Mock Exam records
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            score INTEGER,
            total INTEGER,
            topic TEXT,
            taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ SQLite Database initialized at: {DB_PATH}")


def save_articles(articles_list):
    """
    Inserts a list of summarized articles into the database.
    Ignores duplicates automatically based on unique titles.
    Returns the count of newly inserted articles.
    """
    if not articles_list:
        return 0

    init_db()  # Ensure database is set up
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Use current timestamp for this batch run to group them
    batch_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_inserts = 0

    for article in articles_list:
        try:
            # We use INSERT OR IGNORE to automatically bypass duplicates
            cursor.execute("""
                INSERT OR IGNORE INTO articles (title, source, link, publish_date, summary, category, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                article.get("title"),
                article.get("source"),
                article.get("link"),
                article.get("publish_date"),
                article.get("summary"),
                article.get("category", "General"),
                batch_timestamp
            ))
            if cursor.rowcount > 0:
                new_inserts += 1
        except Exception as e:
            print(f"❌ Error inserting article '{article.get('title')}': {e}")

    conn.commit()
    conn.close()
    print(f"💾 Database Sync: Inserted {new_inserts} new articles out of {len(articles_list)} fetched.")
    
    # Run automatic cleanup of data older than 3 months
    purge_old_articles()
    
    return new_inserts


def purge_old_articles():
    """Automatically purges articles older than 3 months to maintain a rolling window."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DELETE FROM articles 
            WHERE datetime(extracted_at) < datetime('now', '-3 months')
        """)
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            print(f"🧹 Database Cleanup: Purged {deleted_count} historical articles older than 3 months.")
        conn.commit()
    except Exception as e:
        print(f"❌ Error during historical purge: {e}")
    finally:
        conn.close()


def get_latest_news():
    """
    Retrieves all articles from the most recent batch run.
    Returns a dictionary matching the API schema: {generated_at, total_articles, articles}
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Find the most recent batch run timestamp
    cursor.execute("SELECT MAX(extracted_at) FROM articles")
    row = cursor.fetchone()
    
    if not row or row[0] is None:
        conn.close()
        return {"error": "No summary files found"}

    latest_timestamp = row[0]

    # Fetch all articles matching that exact timestamp
    cursor.execute("""
        SELECT title, source, link, publish_date, summary, category, extracted_at 
        FROM articles 
        WHERE extracted_at = ?
    """, (latest_timestamp,))
    
    rows = cursor.fetchall()
    conn.close()

    articles = []
    for r in rows:
        articles.append({
            "title": r["title"],
            "source": r["source"],
            "link": r["link"],
            "publish_date": r["publish_date"],
            "summary": r["summary"],
            "category": r["category"]
        })

    return {
        "generated_at": latest_timestamp,
        "total_articles": len(articles),
        "articles": articles
    }


def get_articles_by_timeframe(week_offset=None, month_offset=None):
    """
    Queries archived articles based on relative week or month offsets.
    E.g. week_offset=0 (current week), week_offset=1 (previous week).
         month_offset=0 (current month), month_offset=1 (previous month).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT title, source, link, publish_date, summary, category FROM articles"
    params = []

    if week_offset is not None:
        # Filter for articles in a specific week offset (use days modifier since SQLite has no week modifier)
        query += " WHERE strftime('%Y-%W', extracted_at) = strftime('%Y-%W', 'now', ?)"
        params.append(f"-{week_offset * 7} days")
    elif month_offset is not None:
        # Filter for articles in a specific month offset
        query += " WHERE strftime('%Y-%m', extracted_at) = strftime('%Y-%m', 'now', ?)"
        params.append(f"-{month_offset} months")

    query += " ORDER BY extracted_at DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    articles = []
    for r in rows:
        articles.append({
            "title": r["title"],
            "source": r["source"],
            "link": r["link"],
            "publish_date": r["publish_date"],
            "summary": r["summary"],
            "category": r["category"]
        })
    return articles


def search_articles(query_str: str, limit: int = 3):
    """
    Searches recent database articles matching query keywords.
    Falls back to returning empty list if no query is present or if no keywords match.
    """
    import re
    if not query_str or not query_str.strip():
        return []

    # Extract alphanumeric words/tokens of length >= 4
    words = re.findall(r'\b\w{4,}\b', query_str.lower())
    
    # Common stop words to exclude from keyword search
    stop_words = {
        "what", "where", "when", "that", "this", "from", "with", "about", 
        "your", "their", "them", "then", "there", "some", "more", "most", 
        "have", "been", "were", "would", "could", "should", "please", "explain",
        "show", "tell", "give", "find", "search", "about", "article", "news"
    }
    keywords = [w for w in words if w not in stop_words]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if not keywords:
        conn.close()
        return []

    # Build SQL query dynamically to match ANY keyword in title or summary
    where_clauses = []
    params = []
    for kw in keywords:
        where_clauses.append("(title LIKE ? OR summary LIKE ?)")
        params.extend([f"%{kw}%", f"%{kw}%"])
        
    sql_query = (
        "SELECT title, source, link, publish_date, summary, category "
        "FROM articles "
        "WHERE " + " OR ".join(where_clauses) + " "
        "ORDER BY extracted_at DESC LIMIT ?"
    )
    params.append(limit)
    
    try:
        cursor.execute(sql_query, params)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"❌ Error during database keyword search: {e}")
        rows = []
    finally:
        conn.close()
        
    articles = []
    for r in rows:
        articles.append({
            "title": r["title"],
            "source": r["source"],
            "link": r["link"],
            "publish_date": r["publish_date"],
            "summary": r["summary"],
            "category": r["category"]
        })
    return articles

