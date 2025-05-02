import sqlite3
import datetime
import os
from pathlib import Path

# Create data directory if it doesn't exist
Path("data").mkdir(exist_ok=True)

def init_db():
    """Initialize the database with the extraction_logs table if it doesn't exist."""
    conn = sqlite3.connect("data/extraction_log.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS extraction_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        filename TEXT NOT NULL,
        method TEXT NOT NULL,
        component_count INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        feedback TEXT,
        feedback_type TEXT,
        file_hash TEXT
    )
    ''')
    conn.commit()
    conn.close()

def compute_file_hash(file_bytes):
    """Compute a hash for the file if bytes are provided."""
    if file_bytes:
        import hashlib
        return hashlib.sha256(file_bytes).hexdigest()
    return None

def log_event(user_email, filename, method, count, feedback=None, feedback_type=None, file_bytes=None):
    """Log an extraction event with protection against SQL injection."""
    file_hash = compute_file_hash(file_bytes) if file_bytes else None
    
    # Input validation
    if not user_email or not filename or not method:
        raise ValueError("Required fields missing for logging")
    
    timestamp = datetime.datetime.now().isoformat()
    
    conn = sqlite3.connect("data/extraction_log.db")
    cursor = conn.cursor()
    
    # Use parameterized query to prevent SQL injection
    cursor.execute(
        """
        INSERT INTO extraction_logs 
        (user_email, filename, method, component_count, timestamp, feedback, feedback_type, file_hash) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, 
        (user_email, filename, method, count, timestamp, feedback, feedback_type, file_hash)
    )
    
    conn.commit()
    conn.close()

def get_user_logs(user_email):
    """Get logs for a specific user with protection against SQL injection."""
    conn = sqlite3.connect("data/extraction_log.db")
    cursor = conn.cursor()
    
    # Use parameterized query to prevent SQL injection
    cursor.execute(
        """
        SELECT filename, method, component_count, timestamp, feedback 
        FROM extraction_logs 
        WHERE user_email = ? 
        ORDER BY timestamp DESC
        """, 
        (user_email,)
    )
    
    results = cursor.fetchall()
    conn.close()
    
    return results