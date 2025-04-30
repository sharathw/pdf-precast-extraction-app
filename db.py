# db.py
import sqlite3
import os
import datetime

# Initialize DB
os.makedirs("data", exist_ok=True)
DB_PATH = os.path.join("data", "extraction_log.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    filename TEXT,
    method TEXT,
    zone TEXT,
    confidence INTEGER
)
''')
conn.commit()
conn.close()

def log_extraction(filename, method, zone, confidence, log_file_txt):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    zone_str = str(zone) if zone else "None"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (timestamp, filename, method, zone, confidence) VALUES (?, ?, ?, ?, ?)",
                   (timestamp, filename, method, zone_str, confidence))
    conn.commit()
    conn.close()

    with open(log_file_txt, "w") as f:
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"File: {filename}\n")
        f.write(f"Method: {method}\n")
        f.write(f"Zone: {zone_str}\n")
        f.write(f"Confidence: {confidence}\n")
