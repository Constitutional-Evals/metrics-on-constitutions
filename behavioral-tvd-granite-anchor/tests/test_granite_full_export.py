"""Offline-only completion guards: billing uncertainty is not missing science."""
import sqlite3
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_granite_exploratory import full_completion_check


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript('CREATE TABLE attempts(run,state,reserve,charged,actual_cost,finished); CREATE TABLE evaluations(run,cid,sid,replica,state);')
        self.pairs=[('constitution','1',0),('__canary__','qc',0)]
        for c,s,k in self.pairs:self.db.execute('INSERT INTO evaluations VALUES(?,?,?,?,?)',('r',c,s,k,'valid'))
    def tearDown(self):self.db.close()
    def check(self):return full_completion_check(self.db,'r',self.pairs)
    def test_settled_unknown_failure_then_success(self):
        self.db.execute("INSERT INTO attempts VALUES('r','retry',100,100,NULL,'time')")
        self.db.execute("INSERT INTO attempts VALUES('r','valid',100,10,'0.00000001','time')")
        before=self.db.serialize();r=self.check()
        self.assertEqual(r['settled_unknown_billing_attempts'],1)
        self.assertEqual(r['conservative_unknown_billing_charges_usd'],1e-7)
        self.assertEqual(before,self.db.serialize())
    def test_reserved_blocks(self):
        self.db.execute("INSERT INTO attempts VALUES('r','reserved',100,0,NULL,NULL)")
        with self.assertRaises(ValueError):self.check()
    def test_missing_science_blocks(self):
        self.db.execute("DELETE FROM evaluations WHERE cid='constitution'")
        with self.assertRaises(ValueError):self.check()
    def test_invalid_science_blocks(self):
        self.db.execute("UPDATE evaluations SET state='invalid' WHERE cid='constitution'")
        with self.assertRaises(ValueError):self.check()
    def test_missing_canary_blocks(self):
        self.db.execute("DELETE FROM evaluations WHERE cid='__canary__'")
        with self.assertRaises(ValueError):self.check()
    def test_inflight_blocks(self):
        self.db.execute("UPDATE evaluations SET state='inflight' WHERE cid='constitution'")
        with self.assertRaises(ValueError):self.check()
    def test_undercharged_unknown_blocks(self):
        self.db.execute("INSERT INTO attempts VALUES('r','retry',100,0,NULL,'time')")
        with self.assertRaises(ValueError):self.check()
    def test_unsettled_unknown_blocks(self):
        self.db.execute("INSERT INTO attempts VALUES('r','retry',100,100,NULL,NULL)")
        with self.assertRaises(ValueError):self.check()
    def test_valid_without_unknown_succeeds(self):
        self.assertEqual(self.check()['settled_unknown_billing_attempts'],0)
