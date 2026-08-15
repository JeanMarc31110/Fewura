from pathlib import Path
import sqlite3
BASE = Path(__file__).resolve().parents[1]
DB = BASE / "data" / "prospect.db"
DB.parent.mkdir(parents=True, exist_ok=True)

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    con = connect()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS prospects(
      id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT NOT NULL,
      category TEXT, address TEXT, postal_code TEXT, city TEXT, region TEXT,
      country TEXT DEFAULT 'France', lat REAL, lon REAL, phone TEXT,
      website TEXT, email TEXT, contact_form_url TEXT, source_url TEXT,
      source_type TEXT, confidence REAL DEFAULT 0, lead_score INTEGER DEFAULT 0,
      email_status TEXT DEFAULT 'inconnu', discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
      last_checked_at TEXT, status TEXT DEFAULT 'nouveau', fingerprint TEXT UNIQUE
    );
    CREATE TABLE IF NOT EXISTS campaigns(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, subject TEXT NOT NULL,
      body TEXT NOT NULL, filter_json TEXT, status TEXT DEFAULT 'brouillon',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS communications(
      id INTEGER PRIMARY KEY AUTOINCREMENT, prospect_id INTEGER, campaign_id INTEGER,
      recipient TEXT, subject TEXT, sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
      status TEXT, provider_message_id TEXT, response_status TEXT, error TEXT
    );
    CREATE TABLE IF NOT EXISTS do_not_contact(
      id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, domain TEXT, company_name TEXT,
      reason TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    con.commit(); con.close()

def rows(sql, params=()):
    con = connect(); out = [dict(r) for r in con.execute(sql, params).fetchall()]; con.close(); return out

def one(sql, params=()):
    con = connect(); r = con.execute(sql, params).fetchone(); con.close(); return dict(r) if r else None

def execute(sql, params=()):
    con = connect(); cur = con.execute(sql, params); con.commit(); rid = cur.lastrowid; con.close(); return rid
