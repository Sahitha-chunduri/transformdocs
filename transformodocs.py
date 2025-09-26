import os
import sys
import json

from config import OUTPUT_FORMATS
from db_ops import init_db
from file_processing import process_file
from ui import create_gui


if __name__ == "__main__":
    init_db()

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        output_format = sys.argv[2] if len(sys.argv) > 2 else 'txt'
        custom_name = sys.argv[3] if len(sys.argv) > 3 else ""
        tags = sys.argv[4] if len(sys.argv) > 4 else ""
        description = sys.argv[5] if len(sys.argv) > 5 else ""
        force_ocr = len(sys.argv) > 6 and sys.argv[6].lower() == 'true'

        if not os.path.exists(file_path):
            print(f"File does not exist: {file_path}")
            sys.exit(1)

        if output_format not in OUTPUT_FORMATS:
            print(f"Unsupported output format: {output_format}")
            print(f"Supported formats: {', '.join(OUTPUT_FORMATS.keys())}")
            sys.exit(1)

        try:
            result = process_file(file_path, output_format, custom_name, tags, description, force_ocr)
            print("Processing completed!")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Processing failed: {e}")
            sys.exit(1)
    else:
        create_gui()


