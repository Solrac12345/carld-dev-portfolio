import os
import json
import pdfplumber
import urllib.request
import urllib.error
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_APP_ROOT = os.path.dirname(os.path.abspath(__file__))
# Many devs name their venv folder ".env", which blocks a ".env" *file*. Use secrets.env locally.
_dotenv_file = os.path.join(_APP_ROOT, ".env")
if os.path.isfile(_dotenv_file):
    load_dotenv(_dotenv_file)
load_dotenv(os.path.join(_APP_ROOT, "secrets.env"))

app = Flask(__name__)

PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Global state for the index
chunks = []
chunk_metadata = []
vectorizer = None
tfidf_matrix = None
_pdf_snapshot = None


def _get_pdf_snapshot():
    """Return a snapshot of PDF files and their modification times."""
    if not os.path.isdir(PDF_DIR):
        return {}
    return {
        f: os.path.getmtime(os.path.join(PDF_DIR, f))
        for f in os.listdir(PDF_DIR)
        if f.lower().endswith(".pdf")
    }


def auto_reload_if_changed():
    """Reload PDFs only when the folder contents have changed."""
    global _pdf_snapshot
    current = _get_pdf_snapshot()
    if current != _pdf_snapshot:
        _pdf_snapshot = current
        load_pdfs()
        count = len(set(m["file"] for m in chunk_metadata))
        print(f"Auto-reloaded: {count} PDF(s), {len(chunks)} chunks.")


def extract_text_from_pdf(filepath):
    """Extract text from a PDF, returning a list of (page_number, text) tuples."""
    pages = []
    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append((page_num, text))
    return pages


def split_into_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks."""
    result = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        result.append(text[start:end])
        start += chunk_size - overlap
    return result


def load_pdfs():
    """Scan the pdfs/ folder, extract text, chunk it, and build the TF-IDF index."""
    global chunks, chunk_metadata, vectorizer, tfidf_matrix

    chunks = []
    chunk_metadata = []

    if not os.path.isdir(PDF_DIR):
        os.makedirs(PDF_DIR, exist_ok=True)
        return

    for filename in os.listdir(PDF_DIR):
        if not filename.lower().endswith(".pdf"):
            continue
        filepath = os.path.join(PDF_DIR, filename)
        pages = extract_text_from_pdf(filepath)
        for page_num, page_text in pages:
            for chunk in split_into_chunks(page_text):
                chunks.append(chunk)
                chunk_metadata.append({"file": filename, "page": page_num})

    if chunks:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(chunks)
    else:
        vectorizer = None
        tfidf_matrix = None


LANG_NAMES = {"en": "English", "fr": "French", "es": "Spanish"}


def call_groq(messages):
    """Call the Groq API and return the assistant's response text."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        GROQ_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": "PortfolioAgent/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Groq API error {e.code}: {body}")
        raise


def ask_llm(question, context_chunks, lang="en"):
    """Send the question and retrieved PDF context to Groq for a natural answer."""
    context = "\n\n".join(
        f"[{c['file']}, page {c['page']}]: {c['text']}"
        for c in context_chunks
    )
    lang_name = LANG_NAMES.get(lang, "English")
    system_msg = (
        f"You are a helpful assistant that answers questions based only on the provided document excerpts. "
        f"If the excerpts don't contain enough information, say so honestly. "
        f"You MUST answer entirely in {lang_name}. "
        f"Do NOT mention document names, file names, or page numbers in your answer."
    )
    user_msg = (
        f"--- DOCUMENT EXCERPTS ---\n{context}\n--- END EXCERPTS ---\n\n"
        f"Question: {question}\n\n"
        f"Answer naturally and concisely in {lang_name}."
    )
    return call_groq([
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ])


@app.after_request
def _security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.route("/")
def index():
    return render_template("portfolio.html")


@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html")


@app.route("/resume/<lang>", methods=["GET"])
def resume_by_lang(lang):
    """Download resume for the specified language."""
    # Map language codes to filenames
    lang_files = {
        "en": "EN.pdf",
        "fr": "FR.pdf",
        "es": "ES.pdf"
    }
    
    filename = lang_files.get(lang)
    if not filename:
        return jsonify({"error": "Invalid language"}), 400
    
    filepath = os.path.join(PDF_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    
    # Download name based on language
    download_names = {
        "en": "Carlos_Tamayo_AI_Developer.pdf",
        "fr": "Carlos_Tamayo_Developpeur_IA.pdf",
        "es": "Carlos_Tamayo_Desarrollador_IA.pdf"
    }
    
    return send_file(filepath, as_attachment=True, download_name=download_names.get(lang, filename))

@app.route("/ask", methods=["POST"])
def ask():
    if not GROQ_API_KEY:
        return jsonify({"error": "AI features are not configured on this server."}), 503

    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    lang = data.get("lang", "en")

    if not question:
        return jsonify({"error": "No question provided."}), 400

    auto_reload_if_changed()

    if not chunks or vectorizer is None:
        return jsonify({"error": "No PDFs found. Add PDF files to the pdfs/ folder and try again."}), 400

    query_vec = vectorizer.transform([question])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

    top_n = 3
    top_indices = scores.argsort()[-top_n:][::-1]

    results = []
    for idx in top_indices:
        score = float(scores[idx])
        if score > 0:
            results.append({
                "text": chunks[idx],
                "file": chunk_metadata[idx]["file"],
                "page": chunk_metadata[idx]["page"],
                "score": round(score, 4),
            })

    if not results:
        return jsonify({"answer": "I couldn't find anything related to your question in the loaded PDFs.", "results": []})

    try:
        answer = ask_llm(question, results, lang=lang)
    except RuntimeError:
        return jsonify({"error": "AI features are not configured on this server."}), 503
    except Exception as e:
        print(f"Ask LLM error: {e}")
        return jsonify({"error": "The AI service is temporarily unavailable."}), 502
    return jsonify({"answer": answer, "results": results})


@app.route("/suggestions", methods=["GET"])
def suggestions():
    if not GROQ_API_KEY:
        return jsonify({"suggestions": []})

    auto_reload_if_changed()
    if not chunks:
        return jsonify({"suggestions": []})

    lang = request.args.get("lang", "en")
    lang_name = LANG_NAMES.get(lang, "English")

    sample = chunks[:10]
    context = "\n\n".join(sample)
    system_msg = "You generate short suggested questions based on document excerpts. Return ONLY a JSON array of strings, nothing else."
    user_msg = (
        f"Based on the following document excerpts, suggest exactly 10 short questions "
        f"a visitor might ask about this person. Write the questions in {lang_name}.\n\n"
        f"{context}\n\n"
        'Example format: ["What is ...?", "How many ...?", "Tell me about ...?", "What are ...?", "Where did ...?"]'
    )
    try:
        raw = call_groq([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ])
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            questions = json.loads(raw[start:end])
        else:
            questions = []
    except Exception as e:
        print(f"Suggestions error: {e}")
        questions = []
    return jsonify({"suggestions": questions[:5]})


def _init_pdf_index():
    global _pdf_snapshot
    load_pdfs()
    _pdf_snapshot = _get_pdf_snapshot()


_init_pdf_index()


if __name__ == "__main__":
    count = len(set(m["file"] for m in chunk_metadata))
    print(f"Loaded {count} PDF(s), {len(chunks)} chunks.")
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=debug, port=port)
