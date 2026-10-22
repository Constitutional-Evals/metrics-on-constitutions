"""Publication-only fixtures; no experiment, remote requests, or real credentials."""
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('sync_snapshot', Path(__file__).resolve().parents[1]/'tools/sync_granite_snapshot.py')
sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name)/'private'; self.dest = Path(self.temp.name)/'public'
        self.prefix = 'behavioral-tvd-granite-anchor'; self.project = self.dest/self.prefix
        for repo in [self.source, self.dest]:
            repo.mkdir(); self.run_git(repo, 'init', '-b', 'main')
            self.run_git(repo, 'config', 'user.name', 'Fixture')
            self.run_git(repo, 'config', 'user.email', 'fixture@example.invalid')
        for name, data in [('analysis.py', b'old analysis\n'), ('README.md', b'private readme\n'), ('frozen.json', b'{"fixed": true}\n')]:
            self.write(self.source/name, data); self.write(self.project/name, data)
        self.commit(self.source)
        self.policy = {'run_id': sync.RUN_ID, 'subdirectory': self.prefix,
                       'allowlist': ['analysis.py', 'README.md', 'frozen.json'],
                       'excluded_paths': ['private/authorization.json'],
                       'frozen_sha256': {'frozen.json': sync.digest((self.source/'frozen.json').read_bytes())}}
        st = sync.tree(self.source, 'HEAD')
        self.baseline = {'run_id': sync.RUN_ID, 'source_commit': sync.commit(self.source, 'HEAD'), 'files': {n: {
            'source_sha256': sync.digest((self.source/n).read_bytes()),
            'destination_sha256': sync.digest((self.project/n).read_bytes()), 'source_blob': st[n][2]} for n in self.policy['allowlist']}}
        self.save_metadata(); self.commit(self.dest)

    @staticmethod
    def run_git(repo, *args):
        return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL)

    def commit(self, repo):
        self.run_git(repo, 'add', '.'); self.run_git(repo, 'commit', '-m', 'fixture')

    @staticmethod
    def write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)

    def save_metadata(self):
        self.write(self.dest/sync.POLICY, sync.encoded(self.policy))
        self.write(self.dest/sync.BASELINE, sync.encoded(self.baseline))

    def plan(self, **kwargs):
        return sync.synchronize(self.source, 'HEAD', self.dest, **kwargs)

    def update_source(self, data=b'new analysis\n'):
        self.write(self.source/'analysis.py', data); self.commit(self.source)

    def test_default_dry_run_does_not_copy_or_commit(self):
        self.update_source(); before = sync.commit(self.dest, 'HEAD')
        report = self.plan()
        self.assertEqual(report['status'], 'ready'); self.assertEqual(len(report['changes']), 1)
        self.assertEqual((self.project/'analysis.py').read_bytes(), b'old analysis\n')
        self.assertEqual(sync.commit(self.dest, 'HEAD'), before)

    def test_explicit_approved_apply_verifies_and_records_baseline(self):
        self.update_source(); report = self.plan(); head = sync.commit(self.dest, 'HEAD')
        self.plan(approved=report)
        self.assertEqual((self.project/'analysis.py').read_bytes(), b'new analysis\n')
        baseline = json.loads((self.dest/sync.BASELINE).read_text())
        self.assertEqual(baseline['source_commit'], sync.commit(self.source, 'HEAD'))
        self.assertEqual(sync.commit(self.dest, 'HEAD'), head)  # No commit or push.
        self.assertTrue((self.dest/'.publication/granite-sync-history'/ (report['manifest_sha256']+'.json')).exists())
        self.commit(self.dest)
        self.assertEqual(self.plan()['changes'], [])  # Idempotent after reviewed commit.

    def test_public_collaborative_change_blocks_even_when_source_unchanged(self):
        self.write(self.project/'analysis.py', b'collaborator\n'); self.commit(self.dest)
        report = self.plan()
        self.assertIn('public_destination_changed', [x['reason'] for x in report['conflicts']])
        with self.assertRaises(sync.Refusal): self.plan(approved=report)
        self.assertEqual((self.project/'analysis.py').read_bytes(), b'collaborator\n')

    def test_changes_on_both_sides_are_conflicts(self):
        self.update_source(); self.write(self.project/'analysis.py', b'collaborator\n'); self.commit(self.dest)
        self.assertEqual(self.plan()['status'], 'blocked')

    def test_stale_approval_refuses_before_any_write(self):
        self.update_source(); report = self.plan(); self.update_source(b'later update\n')
        with self.assertRaises(sync.Refusal): self.plan(approved=report)
        self.assertEqual((self.project/'analysis.py').read_bytes(), b'old analysis\n')

    def test_new_results_are_not_implicitly_allowlisted(self):
        self.write(self.source/'results/batch-0013/probabilities.csv', b'new data\n'); self.commit(self.source)
        report = self.plan(); self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['unapproved_additions'], ['results/batch-0013/probabilities.csv'])
        self.assertFalse((self.project/'results').exists())

    def test_reviewed_exact_new_path_can_be_added(self):
        name = 'results/batch-0013/probabilities.csv'
        self.write(self.source/name, b'new data\n'); self.commit(self.source)
        self.policy['allowlist'].append(name); self.save_metadata(); self.commit(self.dest)
        report = self.plan(); self.assertEqual(report['status'], 'ready')
        self.plan(approved=report); self.assertEqual((self.project/name).read_bytes(), b'new data\n')

    def test_excluded_files_and_database_backups_are_never_copied(self):
        for name in ['private/authorization.json', 'backups/ledger.sqlite.gz', '.env', '.git-extra/ignored.sqlite']:
            self.write(self.source/name, b'private operational state\n')
        self.commit(self.source); report = self.plan()
        self.assertEqual(report['changes'], []); self.assertEqual(report['unapproved_additions'], [])
        self.assertEqual(len(report['excluded_source_paths']), 4)
        self.policy['allowlist'].append('backups/ledger.sqlite.gz'); self.save_metadata(); self.commit(self.dest)
        with self.assertRaises(sync.Refusal): self.plan()

    def test_disguised_database_and_credentials_in_archive_are_rejected(self):
        for data in [gzip.compress(b'SQLite format 3\0database'), gzip.compress(b'sk-or-v1-'+b'Z'*40)]:
            with self.subTest(data=data), self.assertRaises(sync.Refusal):
                sync.inspect_bytes('result.json.gz', data)
            with self.assertRaises(sync.Refusal): sync.inspect_bytes('disguised.json', data)

    def test_frozen_file_change_blocks_publication(self):
        self.write(self.source/'frozen.json', b'{"fixed": false}\n'); self.commit(self.source)
        self.assertIn('frozen_scientific_source_changed', [c['reason'] for c in self.plan()['conflicts']])

    def test_deletion_requires_separate_explicit_approval(self):
        (self.source/'analysis.py').unlink(); self.commit(self.source)
        self.assertEqual(self.plan()['status'], 'blocked')
        report = self.plan(allow_deletions=True); self.assertEqual(report['changes'][0]['action'], 'delete')
        self.plan(allow_deletions=True, approved=report); self.assertFalse((self.project/'analysis.py').exists())

    def test_migration_documentation_overlay_is_not_overwritten(self):
        self.write(self.project/'README.md', b'public documentation\n')
        self.baseline['files']['README.md']['destination_sha256'] = sync.digest(b'public documentation\n')
        self.save_metadata(); self.commit(self.dest)
        self.write(self.source/'README.md', b'updated private documentation\n'); self.commit(self.source)
        self.assertIn('overlay_requires_manual_merge', [c['reason'] for c in self.plan()['conflicts']])

    def test_symlink_and_traversal_are_rejected(self):
        with self.assertRaises(sync.Refusal): sync.safe_path('../private')
        (self.project/'analysis.py').unlink(); (self.project/'analysis.py').symlink_to(self.source/'analysis.py')
        with self.assertRaises(sync.Refusal): self.plan()

    def test_uncommitted_public_changes_block_apply(self):
        self.update_source(); self.write(self.project/'new-collaboration.md', b'uncommitted\n')
        self.assertEqual(self.plan()['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
