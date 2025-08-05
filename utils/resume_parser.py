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
                    page_text = page.extract_text() or ''
                    text += page_text
            if text.strip():
                return text
            else:
                print(f"[WARN] No text extracted from PDF with PyPDF2: {path}. Trying OCR fallback...")
                # OCR fallback
                try:
                    from pdf2image import convert_from_path
                    import pytesseract
                    from PIL import Image
                    ocr_text = ''
                    images = convert_from_path(path)
                    for i, image in enumerate(images):
                        page_ocr = pytesseract.image_to_string(image)
                        ocr_text += page_ocr + '\n'
                    if not ocr_text.strip():
                        print(f"[WARN] OCR also failed to extract text from PDF: {path}")
                    return ocr_text
                except Exception as ocr_e:
                    print(f"[ERROR] OCR extraction failed for PDF {path}: {ocr_e}")
                    return ''
        except Exception as e:
            print(f"[ERROR] Failed to extract text from PDF {path}: {e}")
            return ''
    elif ext in ['.docx', '.doc']:
        try:
            import docx
            doc = docx.Document(path)
            text = '\n'.join([p.text for p in doc.paragraphs])
            if not text.strip():
                print(f"[WARN] No text extracted from DOC/DOCX: {path}")
            return text
        except Exception as e:
            print(f"[ERROR] Failed to extract text from DOC/DOCX {path}: {e}")
            return ''
    else:
        print(f"[WARN] Unsupported file extension for resume: {path}")
        return '' 