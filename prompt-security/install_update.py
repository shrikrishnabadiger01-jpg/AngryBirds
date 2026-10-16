"""Install into an existing prototype, preserving .env/logs and backing up replaced files."""
import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


def install(source, target):
    source=Path(source).resolve();target=Path(target).resolve()
    if source==target:
        raise ValueError('Extract the update outside your existing project first.')
    if not (target/'app.py').exists() or not (target/'core'/'security.py').exists():
        raise ValueError('Target must be the existing prompt-security project.')
    manifest=json.loads((source/'manifest.json').read_text())
    files=[]
    for relative,digest in manifest.items():
        rel=Path(relative)
        if rel.is_absolute() or '..' in rel.parts or rel.parts[0] in ('.env','logs','.venv','backups'):
            raise ValueError('Unsafe manifest entry')
        path=source/rel
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Package verification failed: '+relative)
        compile(path.read_text(encoding='utf-8-sig'),str(path),'exec') if path.suffix=='.py' else None
        files.append(rel)
    backup=target/'backups'/('round2_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True)
    new_files=[]
    # Backup all affected files before the first replacement.
    for rel in files:
        dest=target/rel
        if dest.exists():
            (backup/rel).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(dest,backup/rel)
        else:new_files.append(str(rel))
    (backup/'new_files.json').write_text(json.dumps(new_files,indent=2))
    changed=[]
    try:
        for rel in files:
            dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            changed.append(rel)
            shutil.copy2(source/rel,dest)
    except Exception:
        for rel in changed:
            if (backup/rel).exists():shutil.copy2(backup/rel,target/rel)
            else:(target/rel).unlink(missing_ok=True)
        raise
    print(f'Installed {len(files)} files. Backup: {backup}')
    print('Existing .env, logs, and virtual environment preserved.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--target',required=True);args=parser.parse_args()
    install(Path(__file__).parent,args.target)
