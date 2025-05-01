import sqlite3
from datetime import datetime
import hashlib
import os

DB_PATH = os.path.join("user_db", "user_auth.db")

def init_user_db():
    os.makedirs("user_db", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            role TEXT DEFAULT 'user',
            password TEXT,
            created_at TEXT
)
""")
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(name, email, role, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)", 
                   (name, email, hash_password(password), role, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def authenticate_user(email, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, role FROM users WHERE email = ? AND password = ?", 
                   (email, hash_password(password)))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
