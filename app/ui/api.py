import json
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.storage.db_manager import (
    init_db,
    get_latest_news as db_get_latest_news,
    get_articles_by_timeframe,
    search_articles
)
from app.scheduler.cron_scheduler import start_scheduler
from app.summarizer.ai_summarizer import client

# Explicitly target Llama 3 8B Instruct for fast, interactive student features
MENTOR_MODEL_ID = "meta.llama3-8b-instruct-v1:0"


app = FastAPI()


# Add CORS middleware to allow external connections like Stitch UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev and cross-origin tools
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


OUTPUT_FOLDER = "outputs"


@app.on_event("startup")
def on_startup():
    """Initializes SQLite database and starts background daily scheduler on application launch."""
    print("🚀 [FastAPI] Initializing SQLite database...")
    init_db()
    print("⏰ [FastAPI] Activating daily background cron scheduler...")
    start_scheduler()


@app.get("/", response_class=HTMLResponse)
def home():
    # Serve the beautiful interactive UI dashboard directly
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as file:
            return file.read()
    return "<h3>Frontend UI file not found under app/ui/index.html</h3>"


@app.get("/latest-news")
def get_latest_news():
    # 1. Try fetching from the SQLite database first
    try:
        db_data = db_get_latest_news()
        if db_data and "error" not in db_data and len(db_data.get("articles", [])) > 0:
            cleaned_articles = []
            for article in db_data["articles"]:
                cleaned_articles.append({
                    "title": article.get("title"),
                    "source": article.get("source"),
                    "link": article.get("link"),
                    "publish_date": article.get("publish_date"),
                    "summary": article.get("summary").replace("\n", " ").strip()
                })
            print("💾 serving latest news from SQLite Database.")
            return {
                "generated_at": db_data.get("generated_at"),
                "total_articles": len(cleaned_articles),
                "articles": cleaned_articles
            }
    except Exception as e:
        print(f"⚠️ SQLite query failed: {e}. Falling back to JSON files.")

    # 2. Fallback to outputs JSON files if DB is empty or fails
    if not os.path.exists(OUTPUT_FOLDER):
        return {"error": "No summary files found"}

    files = [
        f for f in os.listdir(OUTPUT_FOLDER)
        if f.endswith(".json")
    ]

    if not files:
        return {
            "error": "No summary files found"
        }

    # Latest file
    latest_file = sorted(files)[-1]
    file_path = os.path.join(OUTPUT_FOLDER, latest_file)

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    cleaned_articles = []
    for article in data["articles"]:
        cleaned_articles.append({
            "title": article.get("title"),
            "source": article.get("source"),
            "link": article.get("link"),
            "publish_date": article.get("publish_date"),
            "summary": article.get("summary").replace("\n", " ").strip()
        })
    print("📁 Serving latest news from local JSON Cache (Fallback).")
    return {
        "generated_at": data.get("generated_at"),
        "total_articles": data.get("total_articles"),
        "articles": cleaned_articles
    }


@app.get("/generate-mock")
def generate_mock(topic: str = "gs2", week_offset: int = 0):
    """
    Dynamically queries recent articles matching a topic / timeframe from the database,
    and prompts Llama 3 via AWS Bedrock to generate 3 customized UPSC Prelims questions.
    """
    print(f"🎯 [FastAPI] Dynamically generating mock test for topic '{topic}' (week_offset={week_offset})...")
    
    # Query articles from the database for the timeframe
    articles = get_articles_by_timeframe(week_offset=week_offset)
    
    # If no articles found, query wider timeline (month offset 0)
    if not articles:
        articles = get_articles_by_timeframe(month_offset=0)

    # Filter articles loosely by topic keywords if available
    filtered = []
    for art in articles:
        title_summary = (art.get("title", "") + " " + art.get("summary", "")).lower()
        if topic == "gs2":
            # Polity, Governance, IR
            if any(k in title_summary for k in ["court", "constitution", "verdict", "bill", "election", "parliament", "scheme", "policy", "india", "un", "relations", "government"]):
                filtered.append(art)
        elif topic == "gs3":
            # Economy, Science, Tech, Environment
            if any(k in title_summary for k in ["rbi", "bank", "rate", "gdp", "growth", "budget", "inflation", "isro", "nasa", "satellite", "space", "climate", "environment", "pollution"]):
                filtered.append(art)
        else:
            filtered.append(art)

    # Use whatever articles we have (max 5)
    source_articles = filtered[:5] if filtered else articles[:5]

    if not source_articles:
        # Fallback static UPSC questions if no data exists in database
        print("⚠️ No articles in database to generate dynamic questions. Serving high-quality static UPSC questions.")
        return {
            "source": "Static UPSC Prep Bank",
            "questions": [
                {
                    "q": "Which Article of the Constitution guarantees the 'Right to Privacy' as an intrinsic part of the Right to Life and Personal Liberty?",
                    "options": ["Article 14", "Article 19", "Article 21", "Article 32"],
                    "correct": 2,
                    "explanation": "In the landmark K.S. Puttaswamy v. Union of India case (2017), the Supreme Court ruled unanimously that the Right to Privacy is a fundamental right protected under Article 21 of the Indian Constitution."
                },
                {
                    "q": "Consider the following statements regarding the Electoral Bonds Scheme:<br>1. Electoral bonds could be purchased by any citizen of India or entity incorporated in India.<br>2. They carried no interest and were valid for 15 calendar days from the date of issue.",
                    "options": ["1 Only", "2 Only", "Both 1 and 2", "Neither 1 nor 2"],
                    "correct": 2,
                    "explanation": "Both statements are correct. The scheme allowed Indian citizens/companies to buy these interest-free bonds. However, in Feb 2024, the Supreme Court struck down the scheme as unconstitutional."
                },
                {
                    "q": "The term 'Stagflation' refers to which economic state?",
                    "options": [
                        "High inflation coupled with high growth",
                        "Low inflation coupled with low growth",
                        "High inflation coupled with low growth and high unemployment",
                        "None of the above"
                    ],
                    "correct": 2,
                    "explanation": "Stagflation is an economic anomaly characterized by stagnant economic growth, high unemployment, and high inflation, presenting a policy dilemma for central banks."
                }
            ]
        }

    # Format the articles text to send in Bedrock prompt
    articles_text = ""
    for idx, art in enumerate(source_articles, start=1):
        articles_text += f"\n[Article {idx}]\nTITLE: {art['title']}\nSUMMARY: {art['summary']}\n"

    prompt = f"""
You are an expert UPSC current affairs teacher and analyst.
Generate exactly 3 multiple-choice questions (MCQs) for UPSC Prelims based on the following news articles.

Articles:
{articles_text}

Instructions:
1. The questions must be highly relevant to the provided articles and their underlying static concepts.
2. The style must match the exact pattern of UPSC Civil Services Prelims questions (e.g. statement evaluation, conceptual clarity, multi-statement options).
3. Return ONLY a valid JSON array of objects. Do not wrap the JSON in Markdown (no ```json code blocks), do not add any conversational text or preambles.
4. Each object in the JSON array must have the following keys EXACTLY:
   - "q": The question string (evaluate statements or ask conceptual details, you can use <br> for new lines).
   - "options": An array of exactly 4 strings representing the multiple choice options.
   - "correct": An integer from 0 to 3 representing the index of the correct option in the options array.
   - "explanation": A detailed, high-scoring UPSC-focused explanation explaining why that option is correct.
5. IMPORTANT: Do NOT include raw double quotes inside JSON string values. Use single quotes (e.g., 'National Education Policy' or 'GS-III') inside the text to prevent JSON syntax errors. Ensure the output is perfectly parseable by Python's json.loads().

Output JSON:
"""

    try:
        body = {
            "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>",
            "max_gen_len": 2000,
            "temperature": 0.2,
            "top_p": 0.9
        }

        response = client.invoke_model(
            modelId=MENTOR_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response["body"].read())
        raw_output = response_body["generation"].strip()

        # Clean Markdown wrappers and isolate JSON array robustly
        raw_output_clean = raw_output.strip()
        if raw_output_clean.startswith("```json"):
            raw_output_clean = raw_output_clean[7:]
        if raw_output_clean.endswith("```"):
            raw_output_clean = raw_output_clean[:-3]
        raw_output_clean = raw_output_clean.strip()

        # Find the JSON array boundary inside the text to bypass any conversational preambles/postambles
        start_idx = raw_output_clean.find("[")
        end_idx = raw_output_clean.rfind("]")
        if start_idx != -1 and end_idx != -1:
            json_str = raw_output_clean[start_idx:end_idx+1]
        else:
            json_str = raw_output_clean

        questions = json.loads(json_str)
        print("✅ Dynamically generated 3 mock questions using AWS Bedrock.")
        return {
            "source": "Dynamic Bedrock UPSC Generator",
            "questions": questions
        }
    except Exception as e:
        print(f"❌ Error generating dynamic mock test: {e}. Serving high-quality static UPSC questions.")
        return {
            "source": "Static UPSC Prep Bank (Fallback)",
            "questions": [
                {
                    "q": "Which Article of the Constitution guarantees the 'Right to Privacy' as an intrinsic part of the Right to Life and Personal Liberty?",
                    "options": ["Article 14", "Article 19", "Article 21", "Article 32"],
                    "correct": 2,
                    "explanation": "In the landmark K.S. Puttaswamy v. Union of India case (2017), the Supreme Court ruled unanimously that the Right to Privacy is a fundamental right protected under Article 21 of the Indian Constitution."
                },
                {
                    "q": "Consider the following statements regarding the Electoral Bonds Scheme:<br>1. Electoral bonds could be purchased by any citizen of India or entity incorporated in India.<br>2. They carried no interest and were valid for 15 calendar days from the date of issue.",
                    "options": ["1 Only", "2 Only", "Both 1 and 2", "Neither 1 nor 2"],
                    "correct": 2,
                    "explanation": "Both statements are correct. The scheme allowed Indian citizens/companies to buy these interest-free bonds. However, in Feb 2024, the Supreme Court struck down the scheme as unconstitutional."
                },
                {
                    "q": "The term 'Stagflation' refers to which economic state?",
                    "options": [
                        "High inflation coupled with high growth",
                        "Low inflation coupled with low growth",
                        "High inflation coupled with low growth and high unemployment",
                        "None of the above"
                    ],
                    "correct": 2,
                    "explanation": "Stagflation is an economic anomaly characterized by stagnant economic growth, high unemployment, and high inflation, presenting a policy dilemma for central banks."
                }
            ]
        }


class ChatRequest(BaseModel):
    message: str


@app.post("/mentor-chat")
def mentor_chat(request: ChatRequest):
    print(f"💬 [FastAPI] AI Mentor processing query: '{request.message}'...")
    
    # 1. Search for related articles in SQLite database for keyword-based context (RAG)
    related_articles = search_articles(request.message, limit=3)
    
    context_text = ""
    if related_articles:
        context_text = "\n[RELEVANT CURRENT AFFAIRS CONTEXT FROM DATABASE]\n"
        for idx, art in enumerate(related_articles, start=1):
            context_text += f"Article {idx}:\nTITLE: {art['title']}\nSUMMARY: {art['summary']}\n\n"
            
    prompt = f"""
You are an expert UPSC Civil Services IAS Exam Mentor, Coach, and general knowledge chatbot.
Your task is to provide a highly informative, supportive, and perfectly structured academic guide or reference answer to the aspirant's query.

Instructions:
1. Short Doubts vs. Detailed Answer Formats:
   - For small general asked questions or quick doubts (e.g. "What is basic structure?", "Who is APJ Abdul Kalam?", "Why RBI did X?"): Answer concisely using 1-2 clean, well-written paragraphs. Avoid heavy bullet lists for short definitions.
   - For comprehensive answer guidelines, syllabus studies, essays, or detailed analytical queries: Use bold headers and clean, well-spaced bullet points (using '*') or numbered lists (using '1.', '2.') to structure key ideas properly.
2. Broad Conversational Intellect (Like the Internet): Answer general doubts, static textbook concepts (e.g. Lakshmikanth, NCERTs), or general knowledge questions thoroughly and dynamically using your broad pre-trained world knowledge.
3. Incorporate Context: If relevant current affairs context is provided below, seamlessly integrate those recent developments into your explanation to show a premium dynamic-static link.
4. Output Format: ALWAYS write in clean, structured Markdown (use '**' for bold text, '*' or '-' for bullet points, and '1.', '2.' for numbered lists). Avoid writing raw HTML tags in your response; use Markdown formatting instead, as it is parsed and rendered automatically on the portal. Keep the response clean and readable with spaces between sections.

{context_text}

Aspirant's Query:
{request.message}

UPSC Reference Response (Markdown):
"""

    try:
        body = {
            "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>",
            "max_gen_len": 1500,
            "temperature": 0.7,
            "top_p": 0.9
        }

        response = client.invoke_model(
            modelId=MENTOR_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response["body"].read())
        raw_output = response_body["generation"].strip()

        # Clean Markdown wrapping if LLM wraps it in ```html ... ``` or ``` ... ```
        if raw_output.startswith("```html"):
            raw_output = raw_output[7:]
        elif raw_output.startswith("```markdown"):
            raw_output = raw_output[11:]
        elif raw_output.startswith("```"):
            raw_output = raw_output[3:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()

        return {"response": raw_output}
    except Exception as e:
        print(f"❌ Error during mentor chat: {e}")
        return {"response": f"I apologize, Aspirant. I encountered an error while processing your request: {str(e)}. Please try re-phrasing your academic query!"}


