from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import feedparser
# from bs4 import BeautifulSoup
from newspaper import Article
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}
print("Loaded Hugging Face Key:", HF_API_KEY[:10], "********")


# --- Fetch Reddit RSS ---
def fetch_news_articles(topic, max_articles=5):
    url = f"https://news.google.com/rss/search?q={topic}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    feed = feedparser.parse(requests.get(url, headers=headers).content)

    articles = []
    for entry in feed.entries[:max_articles]:
        articles.append({
            "title": entry.title,
            "link": entry.link
        })
    return articles

# --- Scrape Text from URL ---
def extract_text_from_url(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text[:3000]    
        # headers = {'User-Agent': 'Mozilla/5.0'}
        # res = requests.get(url, headers=headers, timeout=10)
        # soup = BeautifulSoup(res.content, "html.parser")
        # paragraphs = soup.find_all("p")
        # return " ".join(p.text for p in paragraphs)[:3000]
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
            json={"inputs": text}
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

    reddit_articles = fetch_news_articles(topic)
    summaries = []
    all_text = ""

    for article in reddit_articles:
        content = extract_text_from_url(article["link"])
        if not content or len(content.strip()) < 200:
            continue
        short_summary = summarize_text_hf(content)
        summaries.append({
            "title": article["title"],
            "link": article["link"],
            "summary": short_summary
        })
        all_text += short_summary + " "

    # Final summary of all summaries
    final_summary = summarize_text_hf(all_text) if all_text else "No summaries available."

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
