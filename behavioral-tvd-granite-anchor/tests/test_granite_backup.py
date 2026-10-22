import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from granite_backup import compress_snapshot,create_snapshot,inventory,resolve_snapshot,restore_check


class BackupTests(unittest.TestCase):
    def test_full_and_delta_chain_restore_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'backups';p.mkdir();source=p/'batch-0008-ledger.sqlite'
            db=sqlite3.connect(source);db.execute('CREATE TABLE evidence(id PRIMARY KEY,record)');db.execute("INSERT INTO evidence VALUES(1,'original failed attempt')");db.commit();db.close()
            original=source.read_bytes();r=compress_snapshot(source,retire=True)
            self.assertFalse(source.exists());self.assertTrue(r['exact_byte_restore_verified'])
            work=p/'active.db';db=sqlite3.connect(work);db.execute('CREATE TABLE evidence(id PRIMARY KEY,record)');db.execute("INSERT INTO evidence VALUES(1,'original failed attempt')");db.commit()
            for b in [9,10]:
                db.execute('INSERT INTO evidence VALUES(?,?)',(b,'successful response '*10000));db.commit()
                r=create_snapshot(db,p/f'batch-{b:04d}-ledger.sqlite')
                self.assertEqual(r['all_tables'],inventory(work))
                self.assertEqual(resolve_snapshot(p/f'batch-{b:04d}-ledger.sqlite'),r)
            db.close()
            # Exact initial snapshot still recoverable after chained additions.
            r0=json.loads(Path(str(source)+'.recovery.json').read_text())
            self.assertEqual(restore_check(r0['archive_path'],r0['source_sha256']),r0['all_tables'])
            archive=Path(r['archive_path']);data=archive.read_bytes();archive.write_bytes(data[:-8])
            with self.assertRaises(AssertionError):resolve_snapshot(p/'batch-0010-ledger.sqlite')
    def test_authoritative_retirement_refused(self):
        with self.assertRaises(AssertionError):compress_snapshot('/workspace/work/ledger.sqlite',True)


class ReviewedCheckpointLocatorTests(unittest.TestCase):
    def test_reviewed_completed_checkpoint_keeps_original_history(self):
        from granite_backup import checkpoint_for_batch
        from constitution_distance.local import file_hash
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);original=d/'batch-0012-ledger.sqlite'
            self.assertEqual(checkpoint_for_batch(d,12),original)
            target=d/'batch-0012-completed-reviewed-recovery-ledger.sqlite'
            meta=Path(str(target)+'.recovery.json');meta.write_text(json.dumps({'source_sha256':'verified-source'}))
            pointer=d/'batch-0012-current-checkpoint.json'
            pointer.write_text(json.dumps({'batch':12,'original_path':str(target),'metadata_sha256':file_hash(meta),'source_sha256':'verified-source'}))
            self.assertEqual(checkpoint_for_batch(d,12),target)
            self.assertFalse(original.exists())
            meta.write_text('{}')
            with self.assertRaises(AssertionError):checkpoint_for_batch(d,12)
    def test_wrong_batch_pointer_is_rejected(self):
        from granite_backup import checkpoint_for_batch
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'batch-0012-current-checkpoint.json').write_text(json.dumps({'batch':13}))
            with self.assertRaises(AssertionError):checkpoint_for_batch(d,12)
