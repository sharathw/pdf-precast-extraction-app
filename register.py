import streamlit as st
import streamlit.components.v1 as components
import sqlite3
from datetime import datetime
import requests

# --- CONFIG ---
TURNSTILE_SITEKEY = "your-sitekey-here"
TURNSTILE_SECRET = st.secrets["turnstile_secret"]  # Store safely in secrets.toml

DB_PATH = "data/user_db.db"

# --- DB Setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            registered_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (email, registered_at) VALUES (?, ?)", (email, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

# --- CAPTCHA Verification ---
def verify_turnstile(token):
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    response = requests.post(url, data={
        "secret": TURNSTILE_SECRET,
        "response": token
    })
    return response.json().get("success", False)

# --- UI ---
init_db()
st.title("🔐 Register with Email")

email = st.text_input("Enter your email")

# Insert CAPTCHA widget and hidden response box
turnstile_token = st.text_input("Captcha Token (set by JS)", type="hidden")

components.html(f"""
    <form action="" method="POST">
        <div class="cf-turnstile" data-sitekey="{TURNSTILE_SITEKEY}" data-callback="captchaCallback"></div>
        <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
        <script>
        function captchaCallback(token) {{
            const input = window.parent.document.querySelector('input[type=hidden]');
            if (input) {{
                input.value = token;
            }}
        }}
        </script>
    </form>
""", height=80)

if st.button("Register"):
    if not email:
        st.warning("Please enter an email.")
    elif not turnstile_token:
        st.warning("Captcha validation failed.")
    else:
        if verify_turnstile(turnstile_token):
            add_user(email)
            st.success("✅ Registration successful!")
        else:
            st.error("❌ CAPTCHA verification failed.")
