"""Bounded document ingestion. Archives are read in memory, never extracted."""
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

MAX_FILE = 10 * 1024 * 1024
MAX_TOTAL = 30 * 1024 * 1024
MAX_DOCS = 20
MAX_CHARS = 100_000
SUPPORTED = {'.pdf','.docx','.txt','.md','.csv','.json','.log','.eml'}


def safe_name(name):
    path=PurePosixPath(name.replace('\\','/'))
    if path.is_absolute() or '..' in path.parts or ':' in name or '\x00' in name:
        raise ValueError('Unsafe archive filename')
    return str(path)


def extract_text(name, data):
    suffix=Path(name).suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError('Unsupported file type')
    if len(data)>MAX_FILE:
        raise ValueError('File exceeds 10 MB')
    if suffix in {'.pdf','.docx'}:
        result=subprocess.run([sys.executable,'-m','core.upload_worker',suffix],input=data,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,
            cwd=Path(__file__).resolve().parent.parent)
        if result.returncode:
            try:message=json.loads(result.stdout)['error']
            except Exception:message='Could not parse this document'
            raise ValueError(message)
        text=json.loads(result.stdout)['text']
    else:
        try:text=data.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:text=data.decode('utf-16') if data[:2] in (b'\xff\xfe',b'\xfe\xff') else data.decode('cp1252')
            except UnicodeError:raise ValueError('Save text files as UTF-8')
        if '\x00' in text:raise ValueError('Binary content is not supported as a text file')
    if not text.strip():raise ValueError('No readable text found; scanned PDFs need OCR first')
    if len(text)>MAX_CHARS:raise ValueError('Extracted text exceeds 100,000 characters; split the file')
    return text


def ingest(files):
    """files: iterable of (filename, bytes). Return documents plus visible errors."""
    documents={};errors=[];consumed=0;count=0
    def add(name,data):
        nonlocal count
        if count>=MAX_DOCS:raise ValueError('Maximum 20 documents per import')
        count+=1
        text=extract_text(name,data)
        digest=hashlib.sha256(data).hexdigest()
        source_id='upload_'+hashlib.sha256((name+digest).encode()).hexdigest()[:24]
        documents[source_id]={'title':name,'filename':name,'kind':'document',
            'classification':'internal','origin':'upload','file_sha256':digest,
            'content':text,'characters':len(text)}
    for filename,data in files:
        try:
            name=safe_name(filename)
            if len(data)>MAX_FILE:raise ValueError('File exceeds 10 MB')
            consumed+=len(data)
            if consumed>MAX_TOTAL:raise ValueError('Import exceeds 30 MB total; use a smaller batch')
            if Path(name).suffix.lower()!='.zip':
                add(name,data);continue
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members=archive.infolist()
                if len(members)>100:raise ValueError('ZIP exceeds 100 entries')
                if sum(m.file_size for m in members)>MAX_TOTAL:raise ValueError('ZIP expands beyond 30 MB')
                for member in members:
                    if member.is_dir():continue
                    label=name+' / '+member.filename
                    try:
                        safe_name(member.filename)
                        if (member.external_attr>>16)&0o170000==0o120000:raise ValueError('Symlink entries are not accepted')
                        if member.flag_bits&1:raise ValueError('Encrypted ZIP entries are not supported')
                        if member.file_size>MAX_FILE:raise ValueError('Archive member exceeds 10 MB')
                        if member.file_size>max(member.compress_size,1)*200:raise ValueError('Suspicious compression ratio')
                        if Path(member.filename).suffix.lower()=='.zip':raise ValueError('Nested ZIPs are not supported')
                        if Path(member.filename).suffix.lower() not in SUPPORTED:raise ValueError('Unsupported file type; skipped')
                        add(label,archive.read(member))
                    except Exception as exc:errors.append({'file':label,'reason':str(exc)[:300]})
        except subprocess.TimeoutExpired:errors.append({'file':filename,'reason':'Parsing exceeded 20 seconds; split or convert this file'})
        except Exception as exc:errors.append({'file':filename,'reason':str(exc)[:300]})
    return documents,errors
