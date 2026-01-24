from __future__ import annotations

import json
import os
import smtplib
import sqlite3
from contextlib import closing
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
from flask import Flask, jsonify, request, session, send_from_directory
from requests import RequestException
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users.json"
DB_FILE = BASE_DIR / "users.db"
DEFAULT_FROM_EMAIL = os.getenv("MAIL_FROM_ADDRESS")


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_db_connection()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                role TEXT NOT NULL DEFAULT 'Viewer',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def load_users_from_json() -> Dict[str, Dict[str, Any]]:
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return {
                    username: {
                        "password": details.get("password", ""),
                        "full_name": details.get("full_name", username),
                        "email": details.get("email"),
                        "role": details.get("role", "Viewer"),
                    }
                    for username, details in data.items()
                    if isinstance(details, dict)
                }
    except json.JSONDecodeError:
        pass
    return {}


def migrate_users_from_json() -> None:
    """Load existing JSON users into SQLite if the table is empty."""
    json_users = load_users_from_json()
    if not json_users:
        return

    with closing(get_db_connection()) as conn:
        existing_count = conn.execute("SELECT COUNT(1) FROM users").fetchone()[0]
        if existing_count:
            return

        for username, details in json_users.items():
            try:
                conn.execute(
                    """
                    INSERT INTO users (username, password, full_name, email, role)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        details.get("password", ""),
                        details.get("full_name") or username,
                        details.get("email"),
                        details.get("role") or "Viewer",
                    ),
                )
            except sqlite3.IntegrityError:
                continue
        conn.commit()


def lookup_user(login_identifier: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Find a user by username or email."""
    if not login_identifier:
        return None, None

    with closing(get_db_connection()) as conn:
        row = conn.execute(
            "SELECT username, password, full_name, email, role FROM users WHERE username = ?",
            (login_identifier,),
        ).fetchone()
        if row:
            return row["username"], dict(row)

        row = conn.execute(
            "SELECT username, password, full_name, email, role FROM users WHERE lower(email) = ?",
            (login_identifier.lower(),),
        ).fetchone()
        if row:
            return row["username"], dict(row)
    return None, None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with closing(get_db_connection()) as conn:
        row = conn.execute(
            "SELECT username, password, full_name, email, role FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with closing(get_db_connection()) as conn:
        row = conn.execute(
            "SELECT username, password, full_name, email, role FROM users WHERE lower(email) = ?",
            (email.lower(),),
        ).fetchone()
        return dict(row) if row else None


def create_user(username: str, password_hash: str, full_name: str, email: Optional[str], role: str) -> None:
    with closing(get_db_connection()) as conn:
        conn.execute(
            """
            INSERT INTO users (username, password, full_name, email, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, password_hash, full_name, email, role),
        )
        conn.commit()


def get_session_payload() -> Dict[str, Any]:
    """Helper to build the session payload for responses."""
    username = session.get("user")
    if not username:
        return {"authenticated": False}

    user = get_user_by_username(username)
    if not user:
        session.pop("user", None)
        return {"authenticated": False}

    return {
        "authenticated": True,
        "username": username,
        "display_name": user.get("full_name") or username,
        "role": user.get("role", "Viewer"),
        "email": user.get("email"),
    }


app = Flask(__name__, static_folder="static")
app.secret_key = "secret123"  # Demo secret; replace for production

init_db()
migrate_users_from_json()


@app.route("/")
def root() -> Any:
    return send_from_directory(BASE_DIR, "experiment4.html")


@app.route("/experiment4.html")
def serve_experiment4() -> Any:
    return send_from_directory(BASE_DIR, "experiment4.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename: str) -> Any:
    assets_dir = BASE_DIR / "assets"
    return send_from_directory(assets_dir, filename)


@app.post("/api/signup")
def signup() -> Any:
    payload = request.get_json(force=True, silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    full_name = (payload.get("full_name") or "").strip()
    email = (payload.get("email") or "").strip() or None
    role = (payload.get("role") or "Viewer").strip() or "Viewer"

    if not username or not password or not full_name:
        return (
            jsonify({"error": "Username, full name and password are required."}),
            400,
        )

    if get_user_by_username(username):
        return jsonify({"error": "Username already exists."}), 409

    if email and get_user_by_email(email):
        return jsonify({"error": "Email already in use."}), 409

    try:
        create_user(
            username=username,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            email=email,
            role=role,
        )
    except sqlite3.IntegrityError:
        return jsonify({"error": "Unable to create account. Please try again."}), 500

    return (
        jsonify(
            {
                "success": True,
                "message": "Account created successfully. Please sign in.",
                "username": username,
                "full_name": full_name,
            }
        ),
        201,
    )


@app.post("/api/login")
def login() -> Any:
    payload = request.get_json(force=True, silent=True) or {}
    login_identifier = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not login_identifier or not password:
        return jsonify({"error": "Both username and password are required."}), 400

    username, user = lookup_user(login_identifier)
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid username or password."}), 401

    session["user"] = username
    return jsonify(get_session_payload())


@app.post("/api/logout")
def logout() -> Any:
    session.pop("user", None)
    return jsonify({"success": True})


@app.get("/api/session")
def session_info() -> Any:
    return jsonify(get_session_payload())


@app.before_request
def handle_cors_preflight() -> Any:
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        return response
    return None


@app.after_request
def add_cors_headers(response: Any) -> Any:
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = request.host_url.rstrip("/")
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


def build_email_message(
    to_address: str,
    subject: str,
    body: str,
    sender: Optional[str] = None,
) -> EmailMessage:
    """Create an email message object with sane defaults."""
    sender_address = sender or DEFAULT_FROM_EMAIL
    if not sender_address:
        raise ValueError("Missing MAIL_FROM_ADDRESS environment variable.")

    msg = EmailMessage()
    msg["From"] = sender_address
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def send_email_via_smtp(msg: EmailMessage) -> None:
    """Send the email using SMTP credentials from environment variables."""
    smtp_host = os.getenv("MAIL_SMTP_HOST")
    smtp_port = int(os.getenv("MAIL_SMTP_PORT", "587"))
    smtp_user = os.getenv("MAIL_SMTP_USERNAME")
    smtp_password = os.getenv("MAIL_SMTP_PASSWORD")
    use_tls = os.getenv("MAIL_USE_TLS", "true").lower() != "false"

    if not smtp_host or not smtp_user or not smtp_password:
        raise ValueError(
            "SMTP configuration is incomplete. "
            "Please set MAIL_SMTP_HOST, MAIL_SMTP_USERNAME, and MAIL_SMTP_PASSWORD."
        )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)


@app.post("/api/send-email")
def send_email() -> Any:
    payload = request.get_json(force=True, silent=True) or {}
    to_address = (payload.get("to") or "").strip()
    subject = (payload.get("subject") or "Hello from Lets Build Something").strip()
    message_body = (payload.get("message") or "").strip()
    sender_override = (payload.get("from_address") or "").strip() or None

    if not to_address or not message_body:
        return (
            jsonify({"error": "The 'to' email and 'message' fields are required."}),
            400,
        )

    try:
        msg = build_email_message(
            to_address=to_address,
            subject=subject or "Hello from Lets Build Something",
            body=message_body,
            sender=sender_override,
        )
        send_email_via_smtp(msg)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except smtplib.SMTPException as exc:
        return jsonify({"error": f"Unable to send email: {exc}"}), 502

    return jsonify({"success": True, "message": "Email sent successfully."}), 200


def call_openai_chat(prompt: str, api_key_override: Optional[str] = None) -> str:
    """Send a chat completion request to OpenAI."""
    api_key = api_key_override or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key is not configured. Set OPENAI_API_KEY.")

    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    messages = [
        {
            "role": "system",
            "content": (
                "You are MetroDocs AI, an assistant for Kochi Metro Rail Limited's "
                "document portal. Provide concise, professional answers focused on "
                "datasets, uploads, and process guidance. If unsure, ask for more details."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
            "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "300")),
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices")
    if not choices:
        raise ValueError("OpenAI response did not include any choices.")
    message = choices[0].get("message", {})
    content = (message.get("content") or "").strip()
    if not content:
        raise ValueError("OpenAI response was empty.")
    return content


@app.post("/api/chat")
def chat() -> Any:
    payload = request.get_json(force=True, silent=True) or {}
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Please include a message for the assistant."}), 400

    try:
        provided_key = request.headers.get("X-OpenAI-Key")
        reply = call_openai_chat(user_message, api_key_override=provided_key)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RequestException as exc:
        return jsonify({"error": f"Unable to reach OpenAI: {exc}"}), 502
    except Exception as exc:  # pragma: no cover - catch unexpected issues
        return jsonify({"error": f"Assistant error: {exc}"}), 500

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True, port=5008)
