# Transform Docs

**Transform Docs** is an intelligent document processing platform that converts non-machine-readable files into searchable, machine-readable formats. It provides advanced search, batch processing, and a user-friendly interface to make document management fast, efficient, and storage-friendly.

---

## Features

### 1. Intelligent Document Processor
- Automatic readability detection: selects the optimal extraction method (direct text or OCR)
- Supports **11+ file formats** including PDFs, DOCX, TXT, and images
- Eliminates the need for manual classification

### 2. Advanced Database System
- Uses **SQLite with FTS5** extension for full-text indexing
- Stores metadata and enables **fast ranked searches** with Boolean operators and filtering
- Optimized for large document collections

### 3. Comprehensive Search Engine
- Search by file name, tags, metadata, or content
- Ranked results with **content highlighting** for easier discovery
- Supports **wildcard search** and advanced filtering options

### 4. User-Friendly GUI Interface
- **Tkinter-based interface** with drag-and-drop support
- **Batch processing** for multiple files at once
- Real-time **progress tracking** and multiple output formats
- Designed for non-technical users

---

## Tech Stack

- **Frontend / GUI:** Python Tkinter
- **Backend & Processing:** Python, PyTesseract (OCR)
- **Database:** SQLite with FTS5 extension for full-text search
- **Supported File Formats:** PDF, DOCX, TXT, PNG, JPEG, TIFF, and more
- **Search & Indexing:** Full-text indexing, Boolean operators, ranked search, and filtering

---

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/transform-docs.git
```

2. Navigate to the project directory:
```bash
cd transform-docs
```

3. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Usage

1. Run the main application:
```bash
python main.py
```

2. Drag and drop files into the interface or use the file selector

3. The system automatically detects readability and converts documents to searchable format

4. Use the search bar to query documents by name, tags, metadata, or content

5. Export results in multiple formats if needed

---

## Project Highlights

- Reduces storage usage by converting scanned/image PDFs to text-based machine-readable files
- Eliminates manual effort in document classification
- Provides fast, intelligent, and ranked searches with metadata filtering
- Simple, interactive GUI designed for non-technical users

---

## Future Enhancements

- Support for cloud storage integration (Google Drive, Dropbox, etc.)
- Advanced document analytics and trend reports
- Enhanced OCR accuracy using deep learning models for handwriting
