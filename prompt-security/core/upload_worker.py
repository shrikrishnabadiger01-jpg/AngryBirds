"""Parser subprocess; no network or document macros executed."""
import io
import json
import sys
import zipfile
import xml.etree.ElementTree as ET

MAX=100_000

def extract(suffix,data):
    if suffix=='.pdf':
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(data))
        if reader.is_encrypted:raise ValueError('Encrypted PDFs are not supported')
        if len(reader.pages)>100:raise ValueError('PDF exceeds 100 pages; split it')
        parts=[];size=0;readable=False
        for i,page in enumerate(reader.pages,1):
            text=page.extract_text() or ''
            size+=len(text)+30
            if size>MAX:raise ValueError('PDF text exceeds 100,000 characters; split it')
            if text.strip():
                readable=True;parts.append(f'[Page {i}]\n{text}')
            else:parts.append(f'[Page {i}: no extractable text; blank or image-only page]')
        if not readable:raise ValueError('No readable text found; scanned PDFs need OCR first')
        return '\n\n'.join(parts)
    with zipfile.ZipFile(io.BytesIO(data)) as doc:
        members=doc.infolist()
        if len(members)>1000 or sum(m.file_size for m in members)>30*1024*1024:raise ValueError('DOCX expanded content exceeds limits')
        info=doc.getinfo('word/document.xml')
        if info.file_size>10*1024*1024:raise ValueError('DOCX document XML exceeds limits')
        xml=doc.read(info)
        if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:raise ValueError('DOCX entity declarations are not supported')
        root=ET.fromstring(xml);ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paragraphs=[];size=0
        for p in root.findall('.//w:p',ns):
            text=''.join(t.text or '' for t in p.findall('.//w:t',ns))
            size+=len(text)+1
            if size>MAX:raise ValueError('DOCX text exceeds 100,000 characters; split it')
            if text.strip():paragraphs.append(text)
        return '\n\n'.join(paragraphs)

if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(10*1024*1024+1)
        if len(raw)>10*1024*1024:raise ValueError('File exceeds 10 MB')
        text=extract(sys.argv[1],raw)
        print(json.dumps({'text':text}))
    except Exception as exc:
        print(json.dumps({'error':str(exc)[:300]}));sys.exit(1)
