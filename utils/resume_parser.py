import os

def parse_resume(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.pdf':
        try:
            import PyPDF2
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ''
                for page in reader.pages:
                    text += page.extract_text() or ''
            return text
        except Exception as e:
            return ''
    elif ext in ['.docx', '.doc']:
        try:
            import docx
            doc = docx.Document(path)
            return '\n'.join([p.text for p in doc.paragraphs])
        except Exception as e:
            return ''
    else:
        return '' 