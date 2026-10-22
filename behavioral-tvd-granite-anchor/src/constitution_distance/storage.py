"""Transactional checkpoints and a shared, persistent spending ledger.

An interrupted reservation stays held. Never release it merely because a process
restarted: the provider may have billed a request whose response was lost.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import sqlite3
import threading
import uuid

from .core import digest

SCALE = Decimal(1_000_000_000)


def money(value):
    value = Decimal(str(value))
    if not value.is_finite() or value < 0:
        raise ValueError("Money must be finite and nonnegative")
    return int((value * SCALE).to_integral_value(rounding=ROUND_CEILING))


def dollars(nanos):
    return float(Decimal(nanos) / SCALE)


def now():
    return datetime.now(timezone.utc).isoformat()


class BudgetError(RuntimeError):
    pass


class Ledger:
    def __init__(self, path, budget=0):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.cap = money(budget)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, timeout=30, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), cap INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, spec TEXT NOT NULL, metadata TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS evaluations (
                run TEXT NOT NULL, cid TEXT NOT NULL, sid TEXT NOT NULL, replica INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending', record TEXT,
                PRIMARY KEY(run,cid,sid,replica));
            CREATE TABLE IF NOT EXISTS attempts (
                id TEXT PRIMARY KEY, run TEXT NOT NULL, cid TEXT NOT NULL, sid TEXT NOT NULL,
                replica INTEGER NOT NULL, state TEXT NOT NULL, reserve INTEGER NOT NULL,
                charged INTEGER NOT NULL DEFAULT 0, actual_cost TEXT,
                request TEXT NOT NULL, prompt_hash TEXT NOT NULL, response TEXT,
                error TEXT, http_status INTEGER, started TEXT NOT NULL, finished TEXT);
        ''')
        with self.transaction():
            row = self.db.execute("SELECT cap FROM settings WHERE id=1").fetchone()
            if row is None:
                self.db.execute("INSERT INTO settings VALUES(1,?)", (self.cap,))
            elif self.cap and row['cap'] != self.cap:
                if row['cap'] == 0 and not self.db.execute("SELECT 1 FROM attempts LIMIT 1").fetchone():
                    self.db.execute("UPDATE settings SET cap=? WHERE id=1", (self.cap,))
                else:
                    raise BudgetError("Ledger has a different fixed budget; use its original cap or a new ledger")

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def register(self, run, spec, metadata, pairs):
        encoded = json.dumps(spec, sort_keys=True, ensure_ascii=False)
        with self.transaction():
            old = self.db.execute("SELECT spec FROM runs WHERE id=?", (run,)).fetchone()
            if old and old['spec'] != encoded:
                raise ValueError("Run identifier/configuration mismatch")
            self.db.execute("INSERT OR IGNORE INTO runs VALUES(?,?,?)",
                            (run, encoded, json.dumps(metadata)))
            self.db.executemany("INSERT OR IGNORE INTO evaluations(run,cid,sid,replica) VALUES(?,?,?,?)",
                                [(run, *pair) for pair in pairs])

    def totals(self):
        with self.lock:
            row = self.db.execute("SELECT COALESCE(SUM(charged),0) spent, "
                "COALESCE(SUM(CASE WHEN state='reserved' THEN reserve ELSE 0 END),0) held, "
                "COALESCE(SUM(CASE WHEN actual_cost IS NOT NULL THEN charged ELSE 0 END),0) known "
                "FROM attempts").fetchone()
            return {"actual_spending_usd": dollars(row['known']),
                    "conservative_spending_usd": dollars(row['spent']),
                    "outstanding_reservations_usd": dollars(row['held']),
                    "budget_usd": dollars(self.db.execute("SELECT cap FROM settings WHERE id=1").fetchone()[0]),
                    "invocation_budget_usd": dollars(self.cap)}

    def states(self, run):
        with self.lock:
            return {(r['cid'], r['sid'], r['replica']): dict(r)
                    for r in self.db.execute("SELECT * FROM evaluations WHERE run=?", (run,))}

    def claim(self, run, pair, payload, reserve, retry_missing=False, max_requests=None):
        """Reserve money and claim a unique evaluation in the same transaction."""
        with self.transaction():
            key = (run, *pair)
            row = self.db.execute("SELECT state FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?", key).fetchone()
            allowed = {'pending'} | ({'invalid', 'error', 'retry'} if retry_missing else set())
            if not row or row['state'] not in allowed:
                return None
            if max_requests is not None and self.db.execute("SELECT COUNT(*) FROM attempts WHERE run=?", (run,)).fetchone()[0] >= max_requests:
                raise BudgetError("Per-run request cap exhausted (includes retries)")
            used = self.db.execute("SELECT COALESCE(SUM(charged + CASE WHEN state='reserved' THEN reserve ELSE 0 END),0) FROM attempts").fetchone()[0]
            cap = min(self.cap, self.db.execute("SELECT cap FROM settings WHERE id=1").fetchone()[0])
            if used + reserve > cap:
                raise BudgetError("Budget exhausted: request plus outstanding reservations exceeds remaining cap")
            aid = uuid.uuid4().hex
            self.db.execute("INSERT INTO attempts(id,run,cid,sid,replica,state,reserve,request,prompt_hash,started) VALUES(?,?,?,?,?,'reserved',?,?,?,?)",
                (aid, *key, reserve, json.dumps(payload, ensure_ascii=False), digest(payload['messages']), now()))
            self.db.execute("UPDATE evaluations SET state='inflight' WHERE run=? AND cid=? AND sid=? AND replica=?", key)
            return aid

    def settle(self, aid, state, record=None, response=None, error=None, http_status=None):
        usage = response.get('usage', {}) if isinstance(response, dict) else {}
        cost = usage.get('cost')
        try:
            actual = money(cost) if cost is not None and not isinstance(cost, bool) else None
        except (ValueError, ArithmeticError):
            actual = None
        with self.transaction():
            a = self.db.execute("SELECT * FROM attempts WHERE id=?", (aid,)).fetchone()
            if not a or a['state'] != 'reserved':
                raise ValueError("Attempt already settled or unknown")
            charged = a['reserve'] if actual is None else actual
            self.db.execute("UPDATE attempts SET state=?,charged=?,actual_cost=?,response=?,error=?,http_status=?,finished=? WHERE id=?",
                (state, charged, str(cost) if actual is not None else None,
                 json.dumps(response) if response is not None else None, error, http_status, now(), aid))
            self.db.execute("UPDATE evaluations SET state=?,record=? WHERE run=? AND cid=? AND sid=? AND replica=?",
                (state, json.dumps(record, ensure_ascii=False) if record else None,
                 a['run'], a['cid'], a['sid'], a['replica']))
        if actual is not None and actual > a['reserve']:
            raise BudgetError("Actual cost exceeded conservative reservation; stop and reconcile pricing")

    def attempts(self, run):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM attempts WHERE run=? ORDER BY started,id", (run,))]

    def close(self):
        self.db.close()
