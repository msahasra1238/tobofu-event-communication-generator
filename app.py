
import os
import json
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, render_template_string
from dotenv import load_dotenv
from google import genai
from email_validator import validate_email, EmailNotValidError
import resend

# --------------------------------
# LOAD CONFIGURATION
# --------------------------------

load_dotenv()

app = Flask(__name__)

gemini_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

resend_api_key = os.getenv("RESEND_API_KEY")

if resend_api_key:
    resend.api_key = resend_api_key

# Notification history is stored beside app.py.
HISTORY_FILE = Path(__file__).resolve().parent / "notifications.json"


# --------------------------------
# NOTIFICATION HISTORY HELPERS
# --------------------------------

def load_notifications():
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        app.logger.exception("Could not read notification history")

    return []


def save_notification(recipient, subject, status, email_id=None):
    notifications = load_notifications()

    notifications.insert(0, {
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "channel": "Email",
        "recipient": recipient,
        "subject": subject,
        "status": status,
        "email_id": email_id
    })

    # Keep the latest 200 records.
    notifications = notifications[:200]

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as file:
            json.dump(notifications, file, indent=2, ensure_ascii=False)
    except OSError:
        app.logger.exception("Could not save notification history")


def get_email_id(result):
    if isinstance(result, dict):
        return result.get("id")

    return getattr(result, "id", None)


# --------------------------------
# HOME PAGE
# --------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------
# CALENDAR PAGE
# --------------------------------

@app.route("/calendar")
def calendar():
    return render_template("reminder-calendar.html")


# --------------------------------
# NOTIFICATIONS PAGE
# --------------------------------

@app.route("/notifications")
def notifications_page():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TOBOFU | Notifications</title>
        <style>
            * { box-sizing: border-box; }
            body {
                margin: 0;
                padding: 24px;
                font-family: Arial, sans-serif;
                background: #100d20;
                color: #f7f4ff;
            }
            main { max-width: 1000px; margin: 20px auto; }
            h1 { color: #c7a8ff; }
            a, button {
                display: inline-block;
                margin: 5px 5px 12px 0;
                padding: 10px 14px;
                border-radius: 8px;
                border: 1px solid #51466f;
                background: #34294f;
                color: white;
                text-decoration: none;
                cursor: pointer;
            }
            .panel {
                padding: 20px;
                background: #1c1732;
                border: 1px solid #393052;
                border-radius: 12px;
                overflow-x: auto;
            }
            table { width: 100%; border-collapse: collapse; }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #393052;
                overflow-wrap: anywhere;
            }
            th { color: #d6c2ff; }
            .note { color: #c4bdd8; line-height: 1.6; }
            #message { margin: 12px 0; color: #d6c2ff; }
        </style>
    </head>
    <body>
        <main>
            <h1>TOBOFU Notifications</h1>
            <p class="note">
                View email notifications submitted by your application.
                A successful submission means Resend accepted the request;
                it does not guarantee inbox delivery.
            </p>

            <nav>
                <a href="/">Home</a>
                <a href="/calendar">Calendar & Reminders</a>
                <button onclick="loadHistory()">Refresh History</button>
            </nav>

            <section class="panel">
                <p id="message">Loading notification history...</p>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Channel</th>
                            <th>Recipient</th>
                            <th>Subject</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="history"></tbody>
                </table>
            </section>
        </main>

        <script>
            async function loadHistory() {
                const message = document.getElementById("message");
                const history = document.getElementById("history");

                message.textContent = "Loading...";
                history.replaceChildren();

                try {
                    const response = await fetch("/api/notifications");
                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.error || "Could not load history.");
                    }

                    if (!data.notifications.length) {
                        message.textContent = "No email notification history yet.";
                        return;
                    }

                    message.textContent =
                        data.notifications.length + " recent record(s).";

                    data.notifications.forEach(item => {
                        const row = document.createElement("tr");

                        [
                            item.date,
                            item.channel,
                            item.recipient,
                            item.subject,
                            item.status
                        ].forEach(value => {
                            const cell = document.createElement("td");
                            cell.textContent = value || "";
                            row.appendChild(cell);
                        });

                        history.appendChild(row);
                    });
                } catch (error) {
                    message.textContent = "Error: " + error.message;
                }
            }

            loadHistory();
        </script>
    </body>
    </html>
    """)


# --------------------------------
# NOTIFICATION HISTORY API
# --------------------------------

@app.route("/api/notifications")
def notification_history():
    return jsonify({
        "success": True,
        "notifications": load_notifications()
    })


# --------------------------------
# CHECK BACKEND STATUS
# --------------------------------

@app.route("/health")
def health():
    return jsonify({
        "status": "running",
        "gemini_configured": client is not None,
        "email_configured": bool(resend_api_key),
        "app_file": __file__
    })


# --------------------------------
# GENERATE AI CONTENT
# --------------------------------

@app.route("/generate", methods=["POST"])
def generate():
    if client is None:
        return jsonify({
            "error": "Gemini API key is missing. Check your .env file."
        }), 500

    try:
        data = request.get_json(silent=True) or {}

        content_type = str(data.get("type", "captions")).strip().lower()
        event_name = str(data.get("eventName", "")).strip()
        event_date = str(data.get("eventDate", "")).strip()
        venue = str(data.get("venue", "")).strip()
        audience = str(data.get("audience", "")).strip()
        registration = str(data.get("registration", "")).strip()
        details = str(data.get("details", "")).strip()

        if not event_name or not event_date or not venue:
            return jsonify({
                "error": "Please provide the event name, date, and venue."
            }), 400

        event_information = f"""
Event name: {event_name}
Event date: {event_date}
Venue: {venue}
Target audience: {audience or "Not specified"}
Registration information: {registration or "Not provided"}
Additional details: {details or "Not provided"}
"""

        if content_type in ("captions", "whatsapp"):
            prompt = f"""
You are an event communication assistant.
Create three engaging social media captions and one short
WhatsApp invitation using the information below.
Do not invent event details.

{event_information}
"""
        elif content_type == "email":
            prompt = f"""
Write a professional event invitation email with a subject,
greeting, event details, call to action, and polite closing.
Do not invent missing information.

{event_information}
"""
        elif content_type == "faq":
            prompt = f"""
Create a useful FAQ for this event. Use only the supplied facts.
Clearly state when requested information has not been provided.

{event_information}
"""
        else:
            return jsonify({
                "error": "Unsupported content type."
            }), 400

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )

        generated_text = response.text or ""

        if not generated_text.strip():
            return jsonify({
                "error": "The AI returned empty content. Please try again."
            }), 502

        return jsonify({
            "success": True,
            "type": content_type,
            "content": generated_text,
            "result": generated_text
        })

    except Exception:
        app.logger.exception("AI content generation failed")
        return jsonify({
            "error": "Content generation failed. Check the Flask terminal."
        }), 500


# --------------------------------
# SEND A TEST EMAIL
# --------------------------------

@app.route("/test-email", methods=["POST"])
def test_email():
    if not resend_api_key:
        return jsonify({
            "error": "Resend API key is missing. Check your .env file."
        }), 500

    recipient = ""

    try:
        data = request.get_json(silent=True) or {}
        recipient = str(data.get("email", "")).strip()

        if not recipient:
            return jsonify({
                "error": "Please provide a recipient email address."
            }), 400

        validate_email(recipient)

        subject = "TOBOFU Email Test"

        result = resend.Emails.send({
            "from": "TOBOFU <onboarding@resend.dev>",
            "to": [recipient],
            "subject": subject,
            "text": (
                "Your TOBOFU email integration is connected.\n\n"
                "This is a test message from your event communication project."
            )
        })

        email_id = get_email_id(result)
        save_notification(recipient, subject, "Submitted to Resend", email_id)

        return jsonify({
            "success": True,
            "message": "Email request submitted to Resend.",
            "email_id": email_id
        })

    except EmailNotValidError:
        return jsonify({
            "error": "Please enter a valid email address."
        }), 400

    except Exception:
        app.logger.exception("Test email sending failed")

        if recipient:
            save_notification(
                recipient,
                "TOBOFU Email Test",
                "Failed"
            )

        return jsonify({
            "error": "Email sending failed. Check the Flask terminal and Resend setup."
        }), 500


# --------------------------------
# SEND GENERATED EVENT CONTENT
# --------------------------------

@app.route("/send-email", methods=["POST"])
def send_email():
    if not resend_api_key:
        return jsonify({
            "error": "Resend API key is missing. Check your .env file."
        }), 500

    recipient = ""
    subject = "TOBOFU Event Communication"

    try:
        data = request.get_json(silent=True) or {}

        recipient = str(data.get("email", "")).strip()
        subject = str(
            data.get("subject", "TOBOFU Event Communication")
        ).strip()[:200]
        content = str(data.get("content", "")).strip()

        if not recipient:
            return jsonify({
                "error": "Please enter a recipient email address."
            }), 400

        validate_email(recipient)

        if not content:
            return jsonify({
                "error": "Generate content before sending the email."
            }), 400

        result = resend.Emails.send({
            "from": "TOBOFU <onboarding@resend.dev>",
            "to": [recipient],
            "subject": subject or "TOBOFU Event Communication",
            "text": content
        })

        email_id = get_email_id(result)

        save_notification(
            recipient,
            subject or "TOBOFU Event Communication",
            "Submitted to Resend",
            email_id
        )

        return jsonify({
            "success": True,
            "message": "Email request submitted to Resend.",
            "email_id": email_id
        })

    except EmailNotValidError:
        return jsonify({
            "error": "Please enter a valid email address."
        }), 400

    except Exception:
        app.logger.exception("Generated email sending failed")

        if recipient:
            save_notification(
                recipient,
                subject,
                "Failed"
            )

        return jsonify({
            "error": "Email sending failed. Check the Flask terminal and Resend setup."
        }), 500


# --------------------------------
# START FLASK SERVER
# --------------------------------

if __name__ == "__main__":
    app.run(debug=True)
