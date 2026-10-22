"""Offline, lossless, content-addressed SQLite snapshots. Never opens a dispatcher.

Original filenames remain in immutable sidecars; identical byte snapshots share a
single gzip object. A source is retired only after exact restoration and SQLite
verification. The authoritative database is never a retirement candidate.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from constitution_distance.local import file_hash


def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def save_recovery_record(path, record):
    path=Path(path)
    if path.exists():
        assert json.loads(path.read_text())==record
        return
    tmp=Path(str(path)+'.partial')
    with tmp.open('x') as f:
        json.dump(record,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path);sync_directory(path.parent)


def inventory(path):
    db=sqlite3.connect(f'file:{Path(path).resolve()}?mode=ro&immutable=1',uri=True)
    try:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        result={}
        for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            # Names come only from SQLite's own schema, quoted defensively.
            quoted='"'+name.replace('"','""')+'"'
            cols=[r[1] for r in db.execute(f'PRAGMA table_info({quoted})')]
            order=','.join('"'+c.replace('"','""')+'"' for c in cols)
            h=hashlib.sha256();n=0
            for row in db.execute(f'SELECT * FROM {quoted} ORDER BY {order}'):
                h.update(json.dumps(row,ensure_ascii=False,separators=(',',':')).encode());h.update(b'\n');n+=1
            result[name]={'rows':n,'sha256':h.hexdigest()}
        result['schema_sha256']=hashlib.sha256(json.dumps(list(db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name')),separators=(',',':')).encode()).hexdigest()
        return result
    finally:db.close()


def compress_snapshot(source, retire=False):
    source=Path(source).resolve()
    assert '/backups/' in str(source) and source.suffix=='.sqlite','Never retire an authoritative database'
    meta=Path(str(source)+'.recovery.json')
    sha=file_hash(source);objects=source.parent/'objects';objects.mkdir(exist_ok=True)
    archive=objects/(sha+'.sqlite.gz')
    inv=inventory(source)
    if not archive.exists():
        tmp=archive.with_suffix('.gz.partial')
        assert not tmp.exists()
        with source.open('rb') as src,tmp.open('wb') as dst:
            with gzip.GzipFile(filename='',mode='wb',fileobj=dst,compresslevel=6,mtime=0) as z:shutil.copyfileobj(src,z)
            dst.flush();os.fsync(dst.fileno())
        os.replace(tmp,archive);sync_directory(archive.parent)
    restored=restore_check(archive,sha,inv)
    record={'original_path':str(source),'original_bytes':source.stat().st_size,'source_sha256':sha,
            'archive_path':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':file_hash(archive),
            'sqlite_integrity_check':'ok','exact_byte_restore_verified':True,'all_tables':restored,
            'retired_uncompressed_source':retire,'storage_scope':'Same working volume; not off-volume disaster recovery.'}
    save_recovery_record(meta,record)
    # Archive and durable metadata exist before removing a redundant full-size copy.
    assert file_hash(source)==sha
    if retire:source.unlink()
    return record


def resolve_snapshot(source):
    source=Path(source)
    if source.exists():return {'original_path':str(source),'source_sha256':file_hash(source),'uncompressed_available':True}
    r=json.loads(Path(str(source)+'.recovery.json').read_text())
    assert file_hash(r['archive_path'])==r['archive_sha256']
    assert restore_check(r['archive_path'],r['source_sha256'],r['all_tables'])==r['all_tables']
    return r


def checkpoint_for_batch(backup_dir, batch):
    """Resolve a reviewed completed checkpoint without replacing stopped history."""
    backup_dir=Path(backup_dir)
    pointer=backup_dir/f'batch-{batch:04d}-current-checkpoint.json'
    if not pointer.exists():return backup_dir/f'batch-{batch:04d}-ledger.sqlite'
    record=json.loads(pointer.read_text());assert record['batch']==batch
    target=Path(record['original_path'])
    assert target.parent.resolve()==backup_dir.resolve() and target.suffix=='.sqlite'
    metadata=Path(str(target)+'.recovery.json')
    assert file_hash(metadata)==record['metadata_sha256']
    assert json.loads(metadata.read_text())['source_sha256']==record['source_sha256']
    return target


def prior_snapshot(db, backup_dir, batch):
    """Reuse the verified predecessor checkpoint, not a second identical copy."""
    source=checkpoint_for_batch(backup_dir,batch-1)
    record=resolve_snapshot(source)
    # Active ledger includes no uncheckpointed data: compare through SQLite backup
    # into scratch to account for WAL, then every table/schema, not just row counts.
    with tempfile.TemporaryDirectory(prefix='granite-current-',dir=backup_dir) as tmp:
        copy=Path(tmp)/'current.sqlite';dst=sqlite3.connect(copy)
        try:db.backup(dst)
        finally:dst.close()
        assert inventory(copy)==record['all_tables']
    return {'path':str(source),'sha256':record['source_sha256'],'reused_predecessor_snapshot':True,
            'recovery_metadata':str(source)+'.recovery.json','archive_path':record['archive_path'],
            'archive_sha256':record['archive_sha256'],'restore_verified':True}

# Future checkpoints use 64-KiB binary block deltas from a verified predecessor.
# Each delta preserves exact file bytes, not merely SQL-equivalent contents.
import struct


def restore_to(archive, target):
    archive=Path(archive);chain=[]
    while archive.name.endswith('.delta.gz'):
        with gzip.open(archive,'rb') as src:header=json.loads(src.readline())
        base=Path(header['base_archive_path'])
        assert file_hash(base)==header['base_archive_sha256']
        chain.append((archive,header));archive=base
    with gzip.open(archive,'rb') as src,Path(target).open('wb') as dst:shutil.copyfileobj(src,dst)
    for archive,header in reversed(chain):
        assert file_hash(target)==header['base_source_sha256']
        with gzip.open(archive,'rb') as src,Path(target).open('r+b') as dst:
            assert json.loads(src.readline())==header
            while record:=src.read(12):
                assert len(record)==12
                offset,size=struct.unpack('>QI',record);data=src.read(size);assert len(data)==size
                dst.seek(offset);dst.write(data)
            dst.truncate(header['source_bytes'])
        assert file_hash(target)==header['source_sha256']


# Restore either a full gzip object or a chain of exact binary deltas.
def restore_check(archive, expected_hash, expected_inventory=None):
    with tempfile.TemporaryDirectory(prefix='granite-restore-',dir=Path(archive).resolve().parent) as tmp:
        target=Path(tmp)/'isolated.sqlite';restore_to(archive,target)
        assert file_hash(target)==expected_hash,'Restored bytes differ'
        inv=inventory(target)
        if expected_inventory is not None:assert inv==expected_inventory,'Restored tables differ'
        return inv


def create_snapshot(db, target):
    target=Path(target);assert not target.exists() and not Path(str(target)+'.recovery.json').exists()
    batch=int(target.name.split('-')[1]);basepath=checkpoint_for_batch(target.parent,batch-1)
    base=resolve_snapshot(basepath)
    dst=sqlite3.connect(target)
    try:db.backup(dst)
    finally:dst.close()
    sha=file_hash(target);inv=inventory(target)
    archive=target.parent/'objects'/(sha+'.delta.gz');assert not archive.exists()
    header={'block_bytes':65536,'source_bytes':target.stat().st_size,'source_sha256':sha,
            'base_archive_path':base['archive_path'],'base_archive_sha256':base['archive_sha256'],
            'base_source_sha256':base['source_sha256']}
    tmp=Path(str(archive)+'.partial')
    with tempfile.TemporaryDirectory(prefix='granite-delta-',dir=target.parent) as td:
        restored=Path(td)/'base.sqlite';restore_to(base['archive_path'],restored)
        assert file_hash(restored)==base['source_sha256']
        with target.open('rb') as src,restored.open('rb') as old,tmp.open('wb') as raw:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as z:
                z.write((json.dumps(header,sort_keys=True)+'\n').encode());offset=0
                while data:=src.read(65536):
                    if data!=old.read(65536):z.write(struct.pack('>QI',offset,len(data)));z.write(data)
                    offset+=len(data)
            raw.flush();os.fsync(raw.fileno())
    os.replace(tmp,archive);sync_directory(archive.parent)
    restore_check(archive,sha,inv)
    record={'original_path':str(target),'original_bytes':target.stat().st_size,'source_sha256':sha,
            'archive_path':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':file_hash(archive),
            'format':'gzip-64KiB-block-delta-v1','base_recovery_metadata':str(basepath)+'.recovery.json',
            'sqlite_integrity_check':'ok','exact_byte_restore_verified':True,'all_tables':inv,
            'retired_uncompressed_source':True,'storage_scope':'Same working volume; not off-volume disaster recovery.'}
    save_recovery_record(Path(str(target)+'.recovery.json'),record)
    assert file_hash(target)==sha;target.unlink()
    return record
