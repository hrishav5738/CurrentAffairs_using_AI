# import json
# import os
# from datetime import datetime


# OUTPUT_FOLDER = "outputs"


# def save_summary(summary_text):

#     # Create outputs folder if not exists
#     os.makedirs(OUTPUT_FOLDER, exist_ok=True)

#     # Timestamp
#     timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

#     # File path
#     file_path = f"{OUTPUT_FOLDER}/current_affairs_{timestamp}.json"

#     # Data structure
#     data = {
#         "generated_at": timestamp,
#         "summary": summary_text
#     }

#     # Save JSON
#     with open(file_path, "w", encoding="utf-8") as file:

#         json.dump(data, file, indent=4, ensure_ascii=False)

#     print(f"\n✅ Summary saved successfully:\n{file_path}")

#     return file_path

import json
import os
from datetime import datetime

from app.storage.db_manager import save_articles

OUTPUT_FOLDER = "outputs"


def save_summary(articles):
    # 1. Sync directly into SQLite database (handles deduplication automatically)
    save_articles(articles)

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    file_path = f"{OUTPUT_FOLDER}/current_affairs_{timestamp}.json"

    data = {

        "generated_at": timestamp,

        "total_articles": len(articles),

        "articles": articles
    }

    with open(file_path, "w", encoding="utf-8") as file:

        json.dump(data, file, indent=4, ensure_ascii=False)

    print(f"\n✅ JSON Saved Successfully:\n{file_path}")

    return file_path