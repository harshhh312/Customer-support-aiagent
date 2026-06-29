import os
import sqlite3
import json
from typing import Optional, Dict

DB_PATH = os.getenv("MEMORY_DB_PATH", "./data/memory.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_memory
                 (email TEXT PRIMARY KEY, facts TEXT, last_interaction TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_fact(email: str, fact: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT facts FROM user_memory WHERE email=?", (email,))
    row = c.fetchone()
    facts = json.loads(row[0]) if row else []
    facts.append(fact)
    c.execute("INSERT OR REPLACE INTO user_memory (email, facts) VALUES (?, ?)",
              (email, json.dumps(facts)))
    conn.commit()
    conn.close()

def get_facts(email: str) -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT facts FROM user_memory WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []