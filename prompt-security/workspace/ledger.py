"""Atomic, durable simulated-email ledger. Does not send real mail."""
import json
from contextlib import closing
import sqlite3
from pathlib import Path

class EmailLedger:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS emails (run_id TEXT, fingerprint TEXT, payload TEXT, PRIMARY KEY(run_id,fingerprint))')

    def emails(self, run_id):
        with closing(sqlite3.connect(self.path)) as db, db:
            return [json.loads(row[0]) for row in db.execute('SELECT payload FROM emails WHERE run_id=? ORDER BY rowid', (run_id,))]

    def commit(self, run_id, fingerprint, payload, limit):
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM emails WHERE run_id=? AND fingerprint=?', (run_id,fingerprint)).fetchone():
                return False, 'Duplicate email blocked by durable ledger'
            count = db.execute('SELECT COUNT(*) FROM emails WHERE run_id=?', (run_id,)).fetchone()[0]
            if limit is not None and count >= limit:
                return False, 'Email limit reached for this run'
            db.execute('INSERT INTO emails VALUES (?,?,?)', (run_id,fingerprint,json.dumps(payload)))
        return True, 'Email saved to simulated outbox'
