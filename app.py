from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import feedparser
from bs4 import BeautifulSoup
# from newspaper import Article
# from urllib.parse import urlparse, parse_qs
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://gyanpriya.github.io"}})

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}
print("Loaded Hugging Face Key:", HF_API_KEY[:10], "********")
#payload = {"inputs": "This is a simple test to verify Hugging Face summarization."}


# --- Fetch Reddit RSS ---
def fetch_news_articles(topic, max_articles=5):
    topic = topic.strip().lower().replace(" ", "-")
    url = f"https://medium.com/feed/tag/{topic}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    feed = feedparser.parse(requests.get(url, headers=headers).content)
    print("📰 Fetching news articles from:", url)

    articles = []
    for entry in feed.entries:
        print("🔗 Found article link:", entry.link)
        articles.append({
            "title": entry.title,
            "link": entry.link
        })
        if len(articles) >= max_articles:
            break
    return articles

# --- Scrape Text from URL ---
def extract_text_from_url(url):
    try:
        print("🔗 Real article URL:", url)

        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, allow_redirects=True)

        # Get final URL after redirection
        final_url = res.url
        print("🔁 Final article URL:", final_url)

        # Fetch actual content from final URL
        page = requests.get(final_url, headers=headers)
        soup = BeautifulSoup(page.content, "html.parser")

        # Extract paragraph text
        paragraphs = soup.find_all("p")
        text = " ".join([p.get_text() for p in paragraphs])
        print(f"✅ Extracted {len(text)} characters from article")
        return text
    except Exception as e:
        print(f"[ERROR extracting article from {url}]:", e)
        return ""

# --- Call Hugging Face Summarizer ---
def summarize_text_hf(text):
    if not text.strip():
        return "⚠️ No content to summarize."
    print("Calling Hugging Face with:", text[:150])
    try:
        response = requests.post(
            HF_API_URL,
            headers=HEADERS,
            json={"inputs": text},
            timeout=20
        )
        print("Response status code:", response.status_code)
        print("Response content:", response.text)
        
        result = response.json()

        # Better handling of model load messages
        if "error" in result:
            print("HF API Error:", result['error'])
            return "⚠️ Hugging Face model is loading or errored."

        if isinstance(result, list) and 'summary_text' in result[0]:
            return result[0]['summary_text']
        else:
            return "⚠️ Summary could not be generated."
    except requests.exceptions.Timeout:
        print("❌ Hugging Face API timed out.")
        return "⚠️ Hugging Face is taking too long. Try again later."
    except Exception as e:
        print(f"[ERROR] HuggingFace API: {e}")
        return "⚠️ Error during summarization."

@app.route("/")
def home():
    return {"message": "Summarizer backend is running!"}

# --- Flask Route ---
@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.get_json()
    topic = data.get("topic", "")
    print("✅ Topic received from frontend:", topic)

    reddit_articles = fetch_news_articles(topic)
    print(f"🔎 Number of articles fetched for topic '{topic}':", len(reddit_articles))

    summaries = []
    all_text = ""

    for idx,article in enumerate(reddit_articles):
        print(f"➡️ [{idx+1}] Processing article: {article['title']}")
        content = extract_text_from_url(article["link"])
        if not content or len(content.strip()) < 200:
            print(f"⚠️ Skipping article (too short or empty): {article['link']}")
            continue
        short_summary = summarize_text_hf(content)
        print(f"✅ Summary {idx+1}: {short_summary[:100]}...")

        summaries.append({
            "title": article["title"],
            "link": article["link"],
            "summary": short_summary
        })

        all_text += short_summary + " "
    if not all_text:
        print("⚠️ No valid article content to summarize.")

    # Final summary of all summaries
    final_summary = summarize_text_hf(all_text) if all_text else "No summaries available."
    print("🧠 Final consolidated summary:", final_summary[:200], "...")

    return jsonify({
        "article_summaries": summaries,
        "consolidated_summary": final_summary
    })

@app.route("/test-summary")
def test_summary():
    dummy_text = "Artificial Intelligence (AI) has become a transformative technology... [long content here]"
    summary = summarize_text_hf(dummy_text)
    return jsonify({"test_summary": summary})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host="0.0.0.0", port=port)
