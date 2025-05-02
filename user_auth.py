import sqlite3
import bcrypt
import re
import os
from pathlib import Path

# Create data directory if it doesn't exist
Path("data").mkdir(exist_ok=True)

def init_user_db():
    """Initialize user database with a table if it doesn't exist."""
    conn = sqlite3.connect("data/users.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

def validate_email(email):
    """Validate email format."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))

def validate_password(password):
    """Validate password complexity."""
    if len(password) < 8:
        return False
    return True

def add_user(name, email, role, password):
    """Add a new user with proper input validation."""
    # Input validation
    if not name or not email or not role or not password:
        raise ValueError("All fields are required")
    
    if not validate_email(email):
        raise ValueError("Invalid email format")
    
    if not validate_password(password):
        raise ValueError("Password must be at least 8 characters long")
    
    # Check if user already exists
    conn = sqlite3.connect("data/users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", (email,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        raise ValueError("User with this email already exists")
    
    # Hash the password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Insert user with parameterized query
    cursor.execute(
        "INSERT INTO users (name, email, role, password_hash) VALUES (?, ?, ?, ?)",
        (name, email, role, password_hash.decode('utf-8'))
    )
    conn.commit()
    conn.close()

def authenticate_user(email, password):
    """Authenticate a user with protection against SQL injection."""
    if not email or not password:
        return False
    
    conn = sqlite3.connect("data/users.db")
    cursor = conn.cursor()
    
    # Use parameterized query to prevent SQL injection
    cursor.execute("SELECT name, role, password_hash FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
        return user[0], user[1]  # Return name and role
    return False
    
