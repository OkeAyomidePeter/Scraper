import sqlite3
from datetime import datetime, date
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "outreach.db")

def init_db():
    """Initializes the database schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create leads table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            normalized_phone TEXT UNIQUE,
            website TEXT,
            rating REAL,
            reviews INTEGER,
            category TEXT,
            maps_url TEXT,
            status TEXT DEFAULT 'new', -- new, queued, sending, sent, failed
            generated_message TEXT,
            last_messaged_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create configuration/logs table for daily caps
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            date TEXT PRIMARY KEY,
            messages_sent INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

def save_lead(lead_dict):
    """Saves a single lead if it doesn't already exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO leads (name, phone, normalized_phone, website, rating, reviews, category, maps_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead_dict.get('name'),
            lead_dict.get('phone'),
            lead_dict.get('normalized_phone'),
            lead_dict.get('website'),
            lead_dict.get('rating'),
            lead_dict.get('reviews'),
            lead_dict.get('category'),
            lead_dict.get('maps_url')
        ))
        conn.commit()
        return cursor.rowcount > 0 # Returns True if a new row was actually inserted
    except sqlite3.Error as e:
        print(f"DB Error saving lead: {e}")
        return False
    finally:
        conn.close()

def is_lead_already_messaged(normalized_phone):
    """Checks if a business has already been messaged."""
    if not normalized_phone:
        return False
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM leads WHERE normalized_phone = ?", (normalized_phone,))
    result = cursor.fetchone()
    conn.close()
    return result is not None and result[0] in ['sent', 'queued', 'sending']

def queue_message(normalized_phone, message):
    """Stores the generated message and marks it as queued."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE leads 
            SET generated_message = ?, status = 'queued' 
            WHERE normalized_phone = ?
        """, (message, normalized_phone))
        conn.commit()
    finally:
        conn.close()

def get_next_queued_message():
    """Retrieves the next message from the queue and marks it as 'sending'."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT normalized_phone, generated_message, name 
        FROM leads 
        WHERE status = 'queued' 
        ORDER BY created_at ASC 
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        phone = row[0]
        cursor.execute("UPDATE leads SET status = 'sending' WHERE normalized_phone = ?", (phone,))
        conn.commit()
        conn.close()
        return {"phone": row[0], "message": row[1], "name": row[2]}
    conn.close()
    return None

def mark_as_failed(normalized_phone):
    """Marks a message as failed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = 'failed' WHERE normalized_phone = ?", (normalized_phone,))
    conn.commit()
    conn.close()

def mark_as_sent(normalized_phone):
    """Updates status to sent and increments daily count."""
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE leads SET status = 'sent', last_messaged_at = ? WHERE normalized_phone = ?", (datetime.now(), normalized_phone))
        
        # Update daily stats
        cursor.execute("INSERT OR IGNORE INTO stats (date, messages_sent) VALUES (?, 0)", (today,))
        cursor.execute("UPDATE stats SET messages_sent = messages_sent + 1 WHERE date = ?", (today,))
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"DB Error marking sent: {e}")
    finally:
        conn.close()

def get_daily_status():
    """Returns messages sent today and total unique leads."""
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT messages_sent FROM stats WHERE date = ?", (today,))
    row = cursor.fetchone()
    sent_today = row[0] if row else 0
    
    cursor.execute("SELECT COUNT(*) FROM leads")
    total_leads = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'queued'")
    queued_count = cursor.fetchone()[0]
    
    conn.close()
    return {
        "sent_today": sent_today,
        "total_leads": total_leads,
        "queued": queued_count
    }

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
    print(f"Current Stats: {get_daily_status()}")
