import sqlite3
import datetime
from typing import List, Tuple

from config import DB_PATH


def init_db(db_path: str = DB_PATH) -> None:
    """Initialize database with enhanced schema and fixed FTS setup"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS documents
                 (id INTEGER PRIMARY KEY,
                  name TEXT NOT NULL,
                  custom_name TEXT,
                  path TEXT NOT NULL,
                  original_format TEXT,
                  is_machine_readable INTEGER,
                  readable INTEGER,
                  extracted_text_path TEXT,
                  output_format TEXT,
                  output_path TEXT,
                  processing_method TEXT,
                  file_size INTEGER,
                  word_count INTEGER,
                  tags TEXT,
                  description TEXT,
                  ingested_at TEXT,
                  updated_at TEXT)""")

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_name ON documents(name)",
        "CREATE INDEX IF NOT EXISTS idx_custom_name ON documents(custom_name)",
        "CREATE INDEX IF NOT EXISTS idx_original_format ON documents(original_format)",
        "CREATE INDEX IF NOT EXISTS idx_is_machine_readable ON documents(is_machine_readable)",
        "CREATE INDEX IF NOT EXISTS idx_tags ON documents(tags)",
        "CREATE INDEX IF NOT EXISTS idx_ingested_at ON documents(ingested_at)"
    ]

    for index_sql in indexes:
        c.execute(index_sql)

    c.execute("""CREATE TABLE IF NOT EXISTS extracted_texts
                 (doc_id INTEGER PRIMARY KEY,
                  content TEXT,
                  FOREIGN KEY (doc_id) REFERENCES documents (id))""")

    c.execute("DROP TABLE IF EXISTS documents_fts")

    c.execute("""CREATE VIRTUAL TABLE documents_fts USING fts5(
                 doc_id UNINDEXED,
                 name,
                 custom_name,
                 content,
                 tags,
                 description,
                 tokenize = 'porter ascii'
             )""")

    c.execute("DROP TRIGGER IF EXISTS documents_ai")
    c.execute("DROP TRIGGER IF EXISTS documents_ad")
    c.execute("DROP TRIGGER IF EXISTS documents_au")

    conn.commit()
    conn.close()


def insert_document(name: str, custom_name: str, path: str, original_format: str,
                   is_machine_readable: bool, readable: bool, extracted_text_path: str,
                   output_format: str, output_path: str, processing_method: str,
                   file_size: int = 0, word_count: int = 0, tags: str = "",
                   description: str = "", extracted_text: str = "",
                   db_path: str = DB_PATH) -> int:
    """Fixed document insertion with proper FTS population"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    timestamp = datetime.datetime.utcnow().isoformat()

    c.execute("""INSERT INTO documents (name, custom_name, path, original_format, is_machine_readable,
                 readable, extracted_text_path, output_format, output_path, processing_method,
                 file_size, word_count, tags, description, ingested_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (name, custom_name, path, original_format, int(is_machine_readable), int(readable),
               extracted_text_path, output_format, output_path, processing_method, file_size,
               word_count, tags, description, timestamp, timestamp))

    doc_id = c.lastrowid

    if extracted_text:
        c.execute("INSERT OR REPLACE INTO extracted_texts (doc_id, content) VALUES (?, ?)",
                  (doc_id, extracted_text))

    c.execute("""INSERT INTO documents_fts (doc_id, name, custom_name, content, tags, description)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (doc_id, name, custom_name or "", extracted_text or "", tags or "", description or ""))

    conn.commit()
    conn.close()
    return doc_id


def sanitize_fts_query(query: str) -> str:
    import re
    if not query:
        return ""
    query = re.sub(r'[^\w\s\-+]', ' ', query)
    words = [word.strip() for word in query.split() if word.strip()]
    if not words:
        return ""
    if len(words) > 1:
        return f'"{" ".join(words)}"'
    else:
        return f'{words[0]}*'


def search_documents(query: str, search_type: str = "all", readability_filter: str = "all",
                     db_path: str = DB_PATH) -> list:
    if not query.strip():
        return get_all_documents(readability_filter, db_path)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    base_query = """SELECT d.*, et.content FROM documents d 
                    LEFT JOIN extracted_texts et ON d.id = et.doc_id"""

    readability_condition = ""
    if readability_filter == "machine_readable":
        readability_condition = " AND d.is_machine_readable = 1"
    elif readability_filter == "non_machine_readable":
        readability_condition = " AND d.is_machine_readable = 0"

    try:
        if search_type == "name":
            sql = f"""{base_query}
                      WHERE (d.name LIKE ? OR d.custom_name LIKE ?)
                      {readability_condition}
                      ORDER BY d.updated_at DESC"""
            c.execute(sql, (f"%{query}%", f"%{query}%"))

        elif search_type == "content":
            fts_query = sanitize_fts_query(query)
            try:
                sql = f"""{base_query}
                          INNER JOIN documents_fts fts ON d.id = fts.doc_id
                          WHERE documents_fts MATCH ?
                          {readability_condition}
                          ORDER BY bm25(documents_fts) DESC"""
                c.execute(sql, (fts_query,))
                results = c.fetchall()
                if not results and " " in query:
                    words = query.split()
                    word_queries = [f'{word}*' for word in words if word.strip()]
                    if word_queries:
                        fts_query = " OR ".join(word_queries)
                        c.execute(sql, (fts_query,))
                        results = c.fetchall()
                if not results:
                    sql = f"""{base_query}
                              WHERE et.content LIKE ?
                              {readability_condition}
                              ORDER BY d.updated_at DESC"""
                    c.execute(sql, (f"%{query}%",))
                conn.close()
                return results
            except Exception as fts_error:
                print(f"FTS search failed: {fts_error}")
                sql = f"""{base_query}
                          WHERE et.content LIKE ?
                          {readability_condition}
                          ORDER BY d.updated_at DESC"""
                c.execute(sql, (f"%{query}%",))

        elif search_type == "tags":
            sql = f"""{base_query}
                      WHERE d.tags LIKE ?
                      {readability_condition}
                      ORDER BY d.updated_at DESC"""
            c.execute(sql, (f"%{query}%",))

        else:
            fts_query = sanitize_fts_query(query)
            try:
                sql = f"""SELECT DISTINCT d.*, et.content FROM documents d 
                          LEFT JOIN extracted_texts et ON d.id = et.doc_id
                          LEFT JOIN documents_fts fts ON d.id = fts.doc_id
                          WHERE (d.name LIKE ? OR d.custom_name LIKE ? OR d.tags LIKE ? OR d.description LIKE ?
                                 OR (documents_fts MATCH ? AND fts.doc_id IS NOT NULL))
                          {readability_condition}
                          ORDER BY d.updated_at DESC"""
                c.execute(sql, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", fts_query))
                results = c.fetchall()
                if not results and " " in query:
                    words = query.split()
                    word_queries = [f'{word}*' for word in words if word.strip()]
                    if word_queries:
                        fts_query = " OR ".join(word_queries)
                        c.execute(sql, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", fts_query))
                        results = c.fetchall()
                conn.close()
                return results
            except Exception as fts_error:
                print(f"FTS search failed: {fts_error}")
                sql = f"""SELECT DISTINCT d.*, et.content FROM documents d 
                          LEFT JOIN extracted_texts et ON d.id = et.doc_id
                          WHERE (d.name LIKE ? OR d.custom_name LIKE ? OR d.tags LIKE ? OR d.description LIKE ?
                                 OR et.content LIKE ?)
                          {readability_condition}
                          ORDER BY d.updated_at DESC"""
                c.execute(sql, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))

        results = c.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Search error: {e}")
        conn.close()
        return []


def get_all_documents(readability_filter: str = "all", db_path: str = DB_PATH) -> list:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    base_query = """SELECT d.*, et.content FROM documents d 
                    LEFT JOIN extracted_texts et ON d.id = et.doc_id"""

    if readability_filter == "machine_readable":
        base_query += " WHERE d.is_machine_readable = 1"
    elif readability_filter == "non_machine_readable":
        base_query += " WHERE d.is_machine_readable = 0"

    base_query += " ORDER BY d.updated_at DESC"

    c.execute(base_query)
    results = c.fetchall()
    conn.close()
    return results


def rebuild_fts_index(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM documents_fts")
        c.execute("""INSERT INTO documents_fts (doc_id, name, custom_name, content, tags, description)
                     SELECT d.id, d.name, 
                            COALESCE(d.custom_name, ''), 
                            COALESCE(et.content, ''), 
                            COALESCE(d.tags, ''), 
                            COALESCE(d.description, '')
                     FROM documents d
                     LEFT JOIN extracted_texts et ON d.id = et.doc_id""")
        conn.commit()
        print("FTS index rebuilt successfully")
    except Exception as e:
        conn.rollback()
        print(f"Failed to rebuild FTS index: {e}")
        raise e
    finally:
        conn.close()


