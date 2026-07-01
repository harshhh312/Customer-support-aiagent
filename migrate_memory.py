import sqlite3
import json
from app.memory import save_fact   # uses the new vector version

DB_PATH = "./data/memory.db"   # path to your old sqlite file

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT email, facts FROM user_memory")
rows = c.fetchall()
conn.close()

for email, facts_json in rows:
    if facts_json:
        facts = json.loads(facts_json)
        for fact in facts:
            save_fact(email, fact)
        print(f"✅ Migrated {len(facts)} facts for {email}")