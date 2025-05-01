import streamlit as st
import sqlite3
from datetime import datetime
import hashlib
from user_auth import init_user_db, add_user, authenticate_user

DB_PATH = "user_db/user_auth.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(name, email, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, email, password, created_at) VALUES (?, ?, ?, ?)", 
                   (name, email, hash_password(password), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def authenticate_user(email, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE email = ? AND password = ?", 
                   (email, hash_password(password)))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# UI
init_db()
st.title("🔐 Login / Register")

tabs = st.tabs(["Login", "Register"])

with tabs[0]:
    st.subheader("Login")
    login_email = st.text_input("Email", key="login_email")
    login_password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        user = authenticate_user(login_email, login_password)
        if user:
            st.success(f"Welcome back, {user}!")
        else:
            st.error("Invalid email or password.")

with tabs[1]:
    st.subheader("Register")
    name = st.text_input("Name")
    reg_email = st.text_input("Email", key="reg_email")
    reg_password = st.text_input("Password", type="password", key="reg_pass")
    if st.button("Register"):
        if name and reg_email and reg_password:
            try:
                add_user(name, reg_email, reg_password)
                st.success("🎉 Registered successfully! You can now log in.")
            except sqlite3.IntegrityError:
                st.warning("⚠️ Email already registered.")
        else:
            st.warning("Please fill in all fields.")
