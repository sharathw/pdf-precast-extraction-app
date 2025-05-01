import os
from datetime import datetime
import sqlite3

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

DB_PATH = os.path.join("data", "extraction_log.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extraction_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            filename TEXT,
            file BLOB,
            method TEXT,
            component_count INTEGER,
            feedback TEXT,
            feedback_type TEXT,
            timestamp TEXT
)
""")

    conn.commit()
    conn.close()

def log_event(user_email, filename, file_bytes, method, count, feedback, feedback_type):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO extraction_logs 
        (user_email, filename, file, method, component_count, feedback, feedback_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_email,
        filename,
        file_bytes,
        method,
        count,
        feedback,
        feedback_type,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()
