# import os
# import json
# import boto3

# from dotenv import load_dotenv

# from app.fetchers.article_extractor import process_articles


# # Load .env variables
# load_dotenv()


# # Bedrock Client
# client = boto3.client(

#     service_name="bedrock-runtime",

#     region_name=os.getenv("AWS_REGION"),

#     aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),

#     aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
# )



# model_id = "meta.llama3-8b-instruct-v1:0"


# # Chunking Function
# def chunk_list(data, chunk_size):

#     for i in range(0, len(data), chunk_size):

#         yield data[i:i + chunk_size]


# # Summarization Pipeline
# def generate_summaries():

#     # Get extracted articles
#     articles = process_articles()

#     print(f"\nTotal Extracted Articles: {len(articles)}")

#     # Split into chunks of 5
#     article_chunks = list(chunk_list(articles, 5))

#     print(f"Total Chunks: {len(article_chunks)}")

#     all_summaries = []

#     # Process each chunk
#     for chunk_number, chunk in enumerate(article_chunks, start=1):

#         print(f"\nProcessing Chunk {chunk_number}...\n")

#         start_index = (chunk_number - 1) * 5

#         # Prepare article text
#         article_text = "\n\n".join([

#             f"""
#             Article {start_index + i + 1}

#             TITLE:
#             {article['title']}

#             CONTENT:
#             {article['text'][:3000]}
#             """

#             for i, article in enumerate(chunk)

#         ])

#         # Prompt
#         prompt = f"""
# You are an expert UPSC current affairs teacher and analyst.

# Your task is to explain every news article properly for UPSC aspirants.


# Instructions:

# 1. Cover ALL articles provided below.

# 2. For every article:
#    - Explain the background
#    - Explain why the news is important
#    - Mention possible impact on:
#      * India
#      * Governance
#      * Economy
#      * Science & Technology
#      * Environment
#      * International Relations
#      * Society

# 3. Write each explanation in approximately 70-100 words.

# 4. Every explanation must include:
#    - background/context
#    - why this news matters
# #    - possible future implications
# #    - relevance for UPSC aspirants

# 5. Explain concepts properly instead of giving short bullet summaries.

# 6. Use factual information only from the provided article content.
# Do NOT add imaginary facts.

# 7. Mention constitutional bodies, schemes, ministries, international organizations, reports, or policies whenever relevant.

# 8. Group related articles into categories:
#    - Polity & Governance
#    - Economy
#    - Science & Technology
#    - International Relations
#    - Environment
#    - Defence
#    - Sports
#    - Education

# 9. Do NOT skip any article.

# 10. Keep output structured and readable.

# Articles:
# {article_text}
# """

#         # Request body
#         body = {

#             "prompt":
#             f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>",

#             "max_gen_len": 3500,

#             "temperature": 0.6,

#             "top_p": 0.9
#         }

#         # Invoke Bedrock
#         response = client.invoke_model(

#             modelId=model_id,

#             body=json.dumps(body),

#             contentType="application/json",

#             accept="application/json"
#         )

#         # Parse response
#         response_body = json.loads(response["body"].read())

#         chunk_summary = response_body["generation"]

#         all_summaries.append(chunk_summary)

#         print(f"✅ Chunk {chunk_number} Completed")

#     # Combine summaries
#     final_summary = "\n\n".join(all_summaries)

#     return final_summary


# # Run directly
# if __name__ == "__main__":

#     summary = generate_summaries()

#     print(summary)

import os
import json
import boto3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from botocore.config import Config

from app.fetchers.article_extractor import process_articles


# Load .env
load_dotenv()


# Bedrock Client with automatic standard retries
config = Config(
    retries = {
        'max_attempts': 10,
        'mode': 'standard'
    }
)

client = boto3.client(
    service_name="bedrock-runtime",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    config=config
)


# Model
model_id = "meta.llama3-70b-instruct-v1:0"


def summarize_article(article):
    # Prompt
    prompt = f"""
You are an expert UPSC current affairs teacher and analyst.

Analyze the following news article and provide a high-quality, perfectly structured UPSC-focused explanation.

Instructions:
1. Classify the article into exactly one of these categories:
   - Polity & Governance
   - Economy
   - Science & Technology
   - International Relations
   - Environment
   - Defence
   - Sports
   - Education
   - General
   On the first line of your output, write: "Category: <Selected Category Name>".

2. Provide a structured explanation in approximately 100-140 words covering:
   - Background and context of the news (write in a brief introductory paragraph)
   - Why the news matters for UPSC aspirants (write as 2-3 clear bullet points using '*', linking to constitutional bodies, policies, schemes, ministries, reports, or international organizations if relevant)
   - Possible implications for Governance, Economy, Environment, or Science/Tech (write as 1-2 bullet points using '*')

3. Structure your response cleanly using separate, well-spaced paragraphs and bullet points so it is highly readable and easy to scan. Avoid writing single large solid blocks of text.
4. Use factual information only from the provided article content. Do NOT invent imaginary facts.

Article Title:
{article['title']}

Article Content:
{article['text'][:3000]}
"""

    body = {
        "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>",
        "max_gen_len": 1500,
        "temperature": 0.3,
        "top_p": 0.9
    }

    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json"
    )

    response_body = json.loads(response["body"].read())
    summary_raw = response_body["generation"].strip()

    # Parse Category and clean up summary text
    category = "General"
    summary_lines = summary_raw.split("\n")
    cleaned_lines = []
    
    for line in summary_lines:
        line_stripped = line.strip()
        if line_stripped.lower().startswith("category:"):
            # Extract category name
            parsed_cat = line_stripped.split(":", 1)[1].strip()
            # Normalize to match frontend expected tabs
            parsed_cat_lower = parsed_cat.lower()
            if "polity" in parsed_cat_lower or "governance" in parsed_cat_lower:
                category = "Polity & Governance"
            elif "economy" in parsed_cat_lower:
                category = "Economy"
            elif "science" in parsed_cat_lower or "technology" in parsed_cat_lower or "isro" in parsed_cat_lower or "nasa" in parsed_cat_lower:
                category = "Science & Technology"
            elif "environment" in parsed_cat_lower or "climate" in parsed_cat_lower:
                category = "Environment"
            elif "defence" in parsed_cat_lower or "military" in parsed_cat_lower:
                category = "Defence"
            elif "sports" in parsed_cat_lower:
                category = "Sports"
            elif "education" in parsed_cat_lower:
                category = "Education"
            else:
                category = "General"
        else:
            cleaned_lines.append(line)

    summary_text = "\n".join(cleaned_lines).strip()

    # Add artificial delay between requests to be safe
    time.sleep(1)

    return {
        "title": article["title"],
        "source": article["source"],
        "link": article["link"],
        "publish_date": article["publish_date"],
        "summary": summary_text,
        "category": category
    }


def generate_summaries():
    articles = process_articles()
    summarized_articles = []

    print(f"\nTotal Articles: {len(articles)}")

    # Number of parallel workers (reduced to prevent throttling)
    MAX_WORKERS = 2

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_article = {
            executor.submit(summarize_article, article): article
            for article in articles
        }

        for index, future in enumerate(as_completed(future_to_article), start=1):
            try:
                summarized_article = future.result()
                summarized_articles.append(summarized_article)
                print(f"✅ Completed Article {index}")
            except Exception as e:
                print(f"❌ Error: {e}")

    return summarized_articles