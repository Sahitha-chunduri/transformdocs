import os

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), "db", "documents.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Supported file formats categorized by readability
MACHINE_READABLE_FORMATS = {
    'txt': 'Text Files',
    'docx': 'Word Documents',
    'doc': 'Legacy Word Documents',
    'rtf': 'Rich Text Format',
    'odt': 'OpenDocument Text',
    'pdf': 'PDF Files (with text)',
    'csv': 'CSV Files',
    'json': 'JSON Files',
    'xml': 'XML Files',
    'html': 'HTML Files',
    'md': 'Markdown Files'
}

NON_MACHINE_READABLE_FORMATS = {
    'pdf_scan': 'Scanned PDF Files',
    'jpg': 'JPEG Images',
    'jpeg': 'JPEG Images',
    'png': 'PNG Images',
    'tiff': 'TIFF Images',
    'bmp': 'Bitmap Images',
    'gif': 'GIF Images',
    'webp': 'WebP Images'
}

ALL_FORMATS = {**MACHINE_READABLE_FORMATS, **NON_MACHINE_READABLE_FORMATS}

OUTPUT_FORMATS = {
    'txt': 'Plain Text (.txt)',
    'docx': 'Word Document (.docx)',
    'pdf': 'PDF Document (.pdf)',
    'html': 'HTML (.html)',
    'md': 'Markdown (.md)',
    'json': 'JSON (.json)'
}


