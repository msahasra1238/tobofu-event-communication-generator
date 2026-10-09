import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = Flask(__name__)

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key) if api_key else None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "app": "TOBOFU Event Communication Generator",
        "api_key_configured": bool(api_key)
    })


@app.route("/generate", methods=["POST"])
def generate():
    if client is None:
        return jsonify({
            "error": "API key not found. Check your .env file."
        }), 500

    data = request.get_json(silent=True) or {}

    event_name = data.get("eventName", "").strip()
    event_date = data.get("eventDate", "").strip()
    venue = data.get("venue", "").strip()
    audience = data.get("audience", "General audience").strip()
    details = data.get("details", "").strip()
    message_type = data.get("type", "captions")

    if not event_name or not event_date or not venue:
        return jsonify({
            "error": "Please provide the event name, date, and venue."
        }), 400

    prompts = {
        "captions": "Create 3 engaging social media captions and 1 short WhatsApp invitation.",
        "email": "Write a professional event invitation email with a subject line and body.",
        "faq": "Create 8 useful event FAQs and answers. If a fact is not provided, say it is not specified instead of inventing it."
    }

    if message_type not in prompts:
        return jsonify({"error": "Unsupported generator type."}), 400

    prompt = f"""
You are TOBOFU, an AI event communication assistant.

Use only the event facts provided below.
Never invent dates, prizes, fees, eligibility rules, or other facts.
Clearly mark missing information as not specified.

Event name: {event_name}
Date: {event_date}
Venue: {venue}
Target audience: {audience}
Additional details: {details}

Task: {prompts[message_type]}
Use clear, polished formatting.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return jsonify({"result": response.text or "No text was generated."})

    except Exception:
        app.logger.exception("Gemini generation failed")
        return jsonify({
            "error": "AI generation failed. Check your API access, model availability, quota, and internet connection."
        }), 502


if __name__ == "__main__":
    app.run(debug=True)