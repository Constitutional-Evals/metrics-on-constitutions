#!/usr/bin/env python3
"""Local, review-first snapshot sync. No inference, network, commits, or pushes."""
import argparse
import copy
import gzip
import hashlib
import io
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

POLICY = '.publication/granite-policy.json'
BASELINE = '.publication/granite-baseline.json'
RUN_ID = '03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e'
SECRET = re.compile(rb'(?:sk-or-v1-[A-Za-z0-9_-]{25,}|sk-[A-Za-z0-9]{40,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?i:authorization["\s:]+bearer\s+[A-Za-z0-9_.-]{16,}))')


class Refusal(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)+'\n').encode()


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    if result.returncode:
        raise Refusal('Git read failed: '+ ' '.join(args[:2]))
    return result.stdout


def commit(repo, ref):
    return git(repo, 'rev-parse', '--verify', ref+'^{commit}').decode().strip()


def tree(repo, ref):
    result = {}
    for item in git(repo, 'ls-tree', '-r', '-z', ref).split(b'\0'):
        if item:
            info, name = item.split(b'\t', 1)
            mode, kind, oid = info.decode().split()
            result[name.decode()] = (mode, kind, oid)
    return result


def blob(repo, oid):
    return git(repo, 'cat-file', 'blob', oid)


def safe_path(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or str(p) != name or '\\' in name or ':' in name:
        raise Refusal('Unsafe relative publication path')
    return p


def forbidden(name, policy):
    p = safe_path(name)
    if name in policy['excluded_paths']:
        return True
    if any(x in {'.git', '.publication', 'backups', 'work', 'runs', 'models', '__pycache__'} for x in p.parts):
        return True
    if any(x.startswith('.env') for x in p.parts):
        return True
    low = p.name.lower()
    if any(x in low for x in ['.sqlite', '.db.', 'authorization']) or low.endswith(('.db', '.pem', '.key', '.zip', '.safetensors', '.pt', '.pth')):
        return True
    return name.startswith('configs/granite-exploratory-authorizations/')


def inspect_bytes(name, data):
    """Detect recognizable credentials and disguised databases, including archives."""
    source = io.BytesIO(data)
    if data.startswith(b'PK\x03\x04'):
        raise Refusal('ZIP container requires separate review: '+name)
    stream = gzip.GzipFile(fileobj=source) if name.endswith('.gz') or data.startswith(b'\x1f\x8b') else lzma.LZMAFile(source) if name.endswith('.xz') or data.startswith(b'\xfd7zXZ\x00') else source
    tail = b''
    total = 0
    try:
        while part := stream.read(1024*1024):
            total += len(part)
            if total > 2*1024**3:
                raise Refusal('Oversize decoded artifact needs manual review: '+name)
            block = tail+part
            if SECRET.search(block) or b'SQLite format 3\0' in block:
                raise Refusal('Credential/database pattern; publication refused: '+name)
            tail = block[-512:]
    finally:
        stream.close()


def destination_file(root, name):
    safe_path(name)
    target = root/name
    # Reject symlinked files and parents; do not follow them outside the project.
    for path in [target, *target.parents]:
        if path.is_symlink():
            raise Refusal('Destination symlink; review required: '+name)
        if path == root:
            break
    if target.exists() and not target.is_file():
        raise Refusal('Destination is not a regular file: '+name)
    return target


def committed_json(repo, ref, path):
    return json.loads(git(repo, 'show', ref+':'+path))


def plan(source, source_ref, destination, destination_ref='HEAD', allow_deletions=False):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    sc, dc = commit(source, source_ref), commit(destination, destination_ref)
    if commit(destination, 'HEAD') != dc:
        raise Refusal('Destination checkout must be at the specified destination ref')
    if any(git(p, 'rev-parse', '--show-toplevel').decode().strip() != str(p) for p in [source, destination]):
        raise Refusal('Use the top-level source and destination checkout paths')
    policy = committed_json(destination, dc, POLICY)
    baseline = committed_json(destination, dc, BASELINE)
    if baseline['run_id'] != RUN_ID or policy['run_id'] != RUN_ID:
        raise Refusal('Unexpected scientific run ID')
    prefix = str(safe_path(policy['subdirectory']))
    project = destination/prefix
    if project.is_symlink() or not project.is_dir():
        raise Refusal('Invalid destination project directory')
    st = tree(source, sc)
    allowed = policy['allowlist']
    if len(allowed) != len(set(allowed)):
        raise Refusal('Duplicate allowlist entries')
    changes, conflicts = [], []
    source_root = git(source, 'rev-parse', '--show-toplevel').decode().strip()
    if source_root == str(destination):
        raise Refusal('Source and destination must be different repositories')
    if git(destination, 'status', '--porcelain', '--untracked-files=normal').strip():
        conflicts.append({'path': '.', 'reason': 'destination_worktree_not_clean'})
    baseline_files = baseline['files']
    if set(baseline_files)-set(allowed):
        raise Refusal('Policy removed baseline paths; explicit baseline reconciliation required')
    for name in sorted(allowed):
        if forbidden(name, policy):
            raise Refusal('Policy tries to publish forbidden material: '+name)
        prior = baseline_files.get(name)
        target = destination_file(project, name)
        actual = digest(target.read_bytes()) if target.exists() else None
        if actual != (prior['destination_sha256'] if prior else None):
            conflicts.append({'path': name, 'reason': 'public_destination_changed'})
            continue
        item = st.get(name)
        if item and (item[0] not in ['100644', '100755'] or item[1] != 'blob'):
            conflicts.append({'path': name, 'reason': 'source_symlink_or_submodule'})
            continue
        if item and prior and item[2] == prior['source_blob']:
            current = prior['source_sha256']
            payload = None
        elif item:
            payload = blob(source, item[2]); current = digest(payload)
        else:
            payload, current = None, None
        frozen = policy['frozen_sha256'].get(name)
        if frozen and current != frozen:
            conflicts.append({'path': name, 'reason': 'frozen_scientific_source_changed'})
            continue
        if prior and current == prior['source_sha256']:
            continue
        if current is None:
            if prior:
                if not allow_deletions:
                    conflicts.append({'path': name, 'reason': 'deletion_disabled'})
                elif prior['source_sha256'] != prior['destination_sha256']:
                    conflicts.append({'path': name, 'reason': 'overlay_requires_manual_merge'})
                else:
                    changes.append({'path': name, 'action': 'delete', 'source_sha256': None, 'destination_before_sha256': actual, 'source_blob': None})
            continue
        if prior and prior['source_sha256'] != prior['destination_sha256'] and current != actual:
            conflicts.append({'path': name, 'reason': 'overlay_requires_manual_merge'})
            continue
        inspect_bytes(name, payload if payload is not None else blob(source, item[2]))
        changes.append({'path': name, 'action': 'converged' if current == actual else 'update' if prior else 'add',
                        'source_sha256': current, 'destination_before_sha256': actual, 'source_blob': item[2], 'mode': item[0]})
    base_tree = tree(source, baseline['source_commit'])
    # Report every new unapproved source path; never implicitly approve results/*.
    unapproved = sorted(p for p in st if p not in base_tree and p not in allowed and not forbidden(p, policy))
    ignored = sorted(p for p in st if forbidden(p, policy))
    report = {'schema': 1, 'run_id': RUN_ID, 'source_commit': sc, 'last_published_source_commit': baseline['source_commit'],
              'destination_commit': dc, 'policy_sha256': digest(encoded(policy)), 'baseline_sha256': digest(encoded(baseline)),
              'allow_deletions': allow_deletions, 'changes': changes, 'conflicts': conflicts, 'unapproved_additions': unapproved,
              'excluded_source_paths': ignored, 'status': 'blocked' if conflicts or unapproved else 'ready',
              'inference_calls': 0, 'commits_or_pushes_performed': False}
    report['manifest_sha256'] = digest(encoded(report))
    return report, policy, baseline


def atomic_write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.sync-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def synchronize(source, source_ref, destination, destination_ref='HEAD', allow_deletions=False, approved=None):
    report, policy, baseline = plan(source, source_ref, destination, destination_ref, allow_deletions)
    if approved is None:
        return report
    if approved != report or report['status'] != 'ready':
        raise Refusal('Approval is stale, mismatched, or contains unresolved conflicts/additions')
    destination = Path(destination).resolve()
    project = destination/policy['subdirectory']
    destination_file(destination, BASELINE)
    destination_file(destination, '.publication/granite-sync-history/placeholder.json')
    payloads = {}
    # Validate all bytes before writing anything. Never read data from a dirty source worktree.
    for change in report['changes']:
        if change['action'] != 'delete':
            data = blob(source, change['source_blob'])
            if digest(data) != change['source_sha256']:
                raise Refusal('Source object hash mismatch')
            inspect_bytes(change['path'], data)
            payloads[change['path']] = data
    # Re-run the whole comparison immediately before mutation, including metadata/HEAD.
    if plan(source, source_ref, destination, destination_ref, allow_deletions)[0] != report:
        raise Refusal('Checkout changed during preparation')
    updated = copy.deepcopy(baseline)
    for change in report['changes']:
        name = change['path']; target = destination_file(project, name)
        if change['action'] == 'delete':
            target.unlink(); del updated['files'][name]
        else:
            if change['action'] != 'converged':
                atomic_write(target, payloads[name], int(change['mode'], 8) & 0o777)
            if digest(target.read_bytes()) != change['source_sha256']:
                raise Refusal('Destination verification failed; restore local checkout before retry')
            updated['files'][name] = {'source_sha256': change['source_sha256'], 'destination_sha256': change['source_sha256'], 'source_blob': change['source_blob']}
    updated.update(source_commit=report['source_commit'], prior_source_commit=baseline['source_commit'],
                   destination_base_commit=report['destination_commit'], change_manifest_sha256=report['manifest_sha256'])
    history = destination/'.publication/granite-sync-history'/ (report['manifest_sha256']+'.json')
    destination_file(destination, str(history.relative_to(destination)))
    atomic_write(history, encoded(report))
    atomic_write(destination/BASELINE, encoded(updated))  # Baseline is written last.
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-ref', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--destination-ref', default='HEAD')
    parser.add_argument('--manifest', type=Path, required=True, help='Write review JSON outside both checkouts')
    parser.add_argument('--apply', action='store_true', help='Apply explicitly approved local changes only; never commit/push')
    parser.add_argument('--approved-manifest', type=Path)
    parser.add_argument('--allow-deletions', action='store_true')
    args = parser.parse_args()
    try:
        if args.apply != bool(args.approved_manifest):
            raise Refusal('--apply and --approved-manifest must be supplied together')
        target = args.manifest.resolve()
        if any(target.is_relative_to(p.resolve()) for p in [args.source, args.destination]):
            raise Refusal('Write review manifests outside both repository checkouts')
        approved = json.loads(args.approved_manifest.read_text()) if args.approved_manifest else None
        report = synchronize(args.source, args.source_ref, args.destination, args.destination_ref, args.allow_deletions, approved)
        atomic_write(target, encoded(report))
        print(json.dumps({'status': report['status'], 'changes': len(report['changes']), 'conflicts': len(report['conflicts']),
                          'unapproved_additions': len(report['unapproved_additions']), 'applied_locally': args.apply, 'inference_calls': 0}))
        return 0 if report['status'] == 'ready' else 2
    except (Refusal, OSError, ValueError, KeyError) as error:
        print('Publication refused: '+str(error))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
