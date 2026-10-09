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

    event_name = str(data.get("eventName", "")).strip()
    event_date = str(data.get("eventDate", "")).strip()
    venue = str(data.get("venue", "")).strip()
    audience = str(
        data.get("audience") or "General audience"
    ).strip()
    registration = str(data.get("registration", "")).strip()
    details = str(data.get("details", "")).strip()
    message_type = data.get("type", "captions")

    if not event_name or not event_date or not venue:
        return jsonify({
            "error": "Please provide the event name, date, and venue."
        }), 400

    prompts = {
        "captions": (
            "Create 3 engaging social media captions and "
            "1 short WhatsApp invitation."
        ),
        "email": """
Write a professional, polished event invitation email ready to send.

Include:
1. A clear subject line.
2. A polite greeting to the target audience.
3. An engaging opening invitation.
4. A short paragraph explaining the event.
5. An easy-to-read event details section containing the event name, date, venue, and target audience.
6. The registration link only if one was provided.
7. A clear call to action.
8. A professional closing signed by the TOBOFU Event Organizing Team.

Rules:
- Use natural, professional English.
- Keep the email between 150 and 220 words.
- Avoid unnecessary repetition.
- Never invent prizes, fees, speakers, deadlines, or other missing facts.
- Mark important missing details as not specified when necessary.
- Output only the subject line and email.
""",
        "faq": (
            "Create 8 useful event FAQs and answers. "
            "If a fact is not provided, say it is not specified."
        )
    }

    if message_type not in prompts:
        return jsonify({
            "error": "Unsupported generator type."
        }), 400

    prompt = f"""
You are TOBOFU, an AI event communication assistant.

Use only the event facts provided below.
Never invent dates, prizes, fees, eligibility rules, or other facts.
Clearly mark missing information as not specified.

Event name: {event_name}
Date: {event_date}
Venue: {venue}
Target audience: {audience}
Registration link: {registration or "Not provided"}
Additional details: {details or "Not provided"}

Task: {prompts[message_type]}

Use clear, polished formatting.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )

        generated_text = response.text

        return jsonify({
            "result": generated_text or "No text was generated."
        })

    except Exception as e:
        app.logger.exception("Gemini generation failed")
        return jsonify({
            "error": str(e)
        }), 502


if __name__ == "__main__":
    app.run(debug=True)